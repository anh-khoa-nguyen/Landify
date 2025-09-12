from celery import shared_task

from apps.users.models import User
from apps.moderation.models import Protest

from ..utils import firebase

@shared_task(name="notify_admins_of_new_protest")
def notify_admins_of_new_protest(protest_id: int):
    """
    Tác vụ nền để gửi thông báo về kháng nghị mới đến tất cả các admin.
    """
    try:
        protest = Protest.objects.select_related("protester", "listing").get(id=protest_id)

        protester_username = protest.protester.get_full_name() or protest.protester.username
        listing_title = protest.listing.title

        title = f"Kháng nghị mới cho tin: '{listing_title}'"
        content = f"Người dùng '{protester_username}' đã gửi một kháng nghị. Vui lòng xem xét."
        related_item = {"type": "protest", "id": protest_id}

        admin_users = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        if not admin_users:
            print("Không tìm thấy admin nào để gửi thông báo.")
            return

        for admin in admin_users:
            firebase.send_firestore_notification(
                user_id=admin.id, category="new_protest", title=title, content=content, related_item=related_item
            )

        print(f"Đã gửi yêu cầu thông báo kháng nghị (ID: {protest_id}) đến {admin_users.count()} admin.")

    except Protest.DoesNotExist:
        print(f"LỖI: Protest với ID {protest_id} không tồn tại.")
    except Exception as e:
        print(f"Lỗi khi gửi thông báo kháng nghị: {e}")


@shared_task(name="notify_user_of_protest_resolution")
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

        firebase.send_firestore_notification(
            user_id=user_id, category="protest_resolution", title=title, content=content, related_item=related_item
        )

        print(f"Đã gửi yêu cầu thông báo kết quả kháng nghị cho user ID: {user_id}")

    except Protest.DoesNotExist:
        print(f"LỖI: Protest với ID {protest_id} không tồn tại.")
    except Exception as e:
        print(f"Lỗi khi gửi thông báo kết quả kháng nghị cho user ID {protest_id}: {e}")
