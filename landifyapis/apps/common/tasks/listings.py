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
