# Third-party Libraries
from bs4 import BeautifulSoup
from celery import shared_task

from .. import utils

# Local Application
from apps.users.models import User
from apps.listings.models import Listing
from apps.moderation.models import Protest

from ..tasks import listings as listing_tasks

import logging
logger = logging.getLogger(__name__)

# ==============================================================================
# LISTING-RELATED TASKS
# ==============================================================================

@shared_task(name="listing.check_for_spam")
def check_listing_for_spam(listing_id: int):
    """
    Tác vụ nền để kiểm tra nội dung của một tin đăng có chứa từ khóa spam hay không.
    """
    # Danh sách từ khóa spam có thể được quản lý trong DB hoặc settings
    SPAM_KEYWORDS = ["khuyến mãi sốc", "vay tiền", "tín dụng đen", "casino", "đánh bạc"]

    try:
        listing = Listing.objects.get(id=listing_id)
        print(f"Bắt đầu kiểm tra spam cho Listing ID: {listing_id}")

        # Làm sạch HTML từ RichTextField để chỉ lấy văn bản thuần túy
        soup = BeautifulSoup(listing.content, "html.parser")
        content_text = soup.get_text().lower()
        title_text = listing.title.lower()

        # Kiểm tra xem có từ khóa spam nào trong tiêu đề hoặc nội dung không
        is_spam_detected = any(keyword in title_text or keyword in content_text for keyword in SPAM_KEYWORDS)

        if is_spam_detected:
            listing.active = False
            listing.spam_check_status = Listing.SpamCheckStatus.FLAGGED
            listing.save(update_fields=["active", "spam_check_status"])
            logger.warning("SPAM ĐÃ ĐƯỢC PHÁT HIỆN trong Listing ID: %s. Tin đã bị vô hiệu hóa.", listing_id)

            # TODO: Kích hoạt một task thông báo cho người dùng về việc tin bị gỡ
            # notify_user_of_listing_rejection.delay(listing_id, "Nội dung chứa từ khóa bị cấm.")

        else:
            listing.spam_check_status = Listing.SpamCheckStatus.CLEAN
            listing.save(update_fields=["spam_check_status"])
            print(f"Listing ID: {listing_id} trong sạch.")

    except Listing.DoesNotExist:
        logger.error("Task 'check_for_spam' thất bại: Listing với ID %s không tồn tại.", listing_id)
    except Exception as e:
        logger.error("Lỗi không xác định (Task) khi kiểm tra spam cho Listing ID %s: %s", listing_id, e)


@shared_task(name="listing.notify_admins_of_new_protest")
def notify_admins_of_new_protest(protest_id: int):
    """
    Tác vụ nền để gửi thông báo về kháng nghị mới (liên quan đến một Listing) đến tất cả các admin.
    """
    try:
        protest = Protest.objects.select_related("protester", "listing").get(id=protest_id)

        protester_username = protest.protester.get_full_name() or protest.protester.username
        listing_title = protest.listing.title

        title = f"Kháng nghị mới cho tin: '{listing_title}'"
        content = f"Người dùng '{protester_username}' đã gửi một kháng nghị. Vui lòng xem xét."
        related_item = {"type": "protest", "id": protest_id}

        admin_users = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        if not admin_users.exists():
            print("Không tìm thấy admin nào để gửi thông báo.")
            return

        for admin in admin_users:
            utils.send_firestore_notification(
                user_id=admin.id, category="new_protest", title=title, content=content, related_item=related_item
            )

        print(f"Đã gửi yêu cầu thông báo kháng nghị (ID: {protest_id}) đến {admin_users.count()} admin.")

    except Protest.DoesNotExist:
        print(f"LỖI (Task): Protest với ID {protest_id} không tồn tại.")
    except Exception as e:
        print(f"Lỗi (Task) khi gửi thông báo kháng nghị: {e}")


@shared_task(name="listing.notify_user_of_protest_resolution")
def notify_user_of_protest_resolution(protest_id: int):
    """
    Tác vụ nền để gửi thông báo về kết quả xử lý kháng nghị cho người dùng.
    """
    try:
        protest = Protest.objects.select_related("protester", "listing").get(id=protest_id)

        user_id = protest.protester.id
        listing_title = protest.listing.title
        protest_status_display = protest.get_status_display()
        resolution_note = protest.resolution_note

        title = f"Kháng nghị của bạn cho tin '{listing_title}' đã được xử lý"
        content = f"Kết quả: {protest_status_display}.\n" f"Ghi chú từ quản trị viên: {resolution_note}"
        related_item = {"type": "listing", "id": protest.listing.id}

        utils.send_firestore_notification(
            user_id=user_id, category="protest_resolution", title=title, content=content, related_item=related_item
        )

        print(f"Đã gửi yêu cầu thông báo kết quả kháng nghị cho user ID: {user_id}")

    except Protest.DoesNotExist:
        print(f"LỖI (Task): Protest với ID {protest_id} không tồn tại.")
    except Exception as e:
        print(f"Lỗi (Task) khi gửi thông báo kết quả kháng nghị cho user ID {protest_id}: {e}")
