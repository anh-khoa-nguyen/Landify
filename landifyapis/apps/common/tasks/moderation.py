from bs4 import BeautifulSoup
from celery import shared_task

from apps.listings.models import Listing

import logging
logger = logging.getLogger(__name__)

# Danh sách từ khóa spam có thể được quản lý trong DB hoặc settings
SPAM_KEYWORDS = ["khuyến mãi sốc", "vay tiền", "tín dụng đen", "casino", "đánh bạc"]


@shared_task(name="check_listing_for_spam")
def check_listing_for_spam(listing_id: int):
    """
    Tác vụ nền để kiểm tra nội dung của một tin đăng có chứa spam hay không.
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        print(f"Bắt đầu kiểm tra spam cho Listing ID: {listing_id}")

        # Làm sạch HTML từ RichTextField để chỉ lấy văn bản thuần túy
        soup = BeautifulSoup(listing.content, "html.parser")
        content_text = soup.get_text().lower()
        title_text = listing.title.lower()

        is_spam_detected = any(keyword in title_text or keyword in content_text for keyword in SPAM_KEYWORDS)

        if is_spam_detected:
            listing.active = False
            listing.spam_check_status = Listing.SpamCheckStatus.FLAGGED
            listing.save(update_fields=["active", "spam_check_status"])
            logger.warning("SPAM ĐÃ ĐƯỢC PHÁT HIỆN trong Listing ID: %s. Tin đã bị vô hiệu hóa.", listing_id)

            # TODO: Kích hoạt một task thông báo cho người dùng về việc tin bị gỡ
            # from .notifications import notify_user_of_listing_rejection
            # notify_user_of_listing_rejection.delay(listing_id, "Nội dung chứa từ khóa bị cấm.")

        else:
            listing.spam_check_status = Listing.SpamCheckStatus.CLEAN
            listing.save(update_fields=["spam_check_status"])
            print(f"Listing ID: {listing_id} trong sạch.")

    except Listing.DoesNotExist:
        print(f"LỖI: Listing với ID {listing_id} không tồn tại.")
    except Exception as e:
        print(f"LỖI không xác định khi kiểm tra spam cho Listing ID {listing_id}: {e}")
