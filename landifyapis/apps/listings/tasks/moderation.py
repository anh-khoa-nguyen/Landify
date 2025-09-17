# apps/listings/tasks/moderation.py
from bs4 import BeautifulSoup
from celery import shared_task
import requests
import logging

from apps.listings.models import Listing
# === THAY ĐỔI IMPORT: Trỏ đến file notifications.py mới ===
from .notifications import notify_user_of_listing_rejection

logger = logging.getLogger(__name__)


@shared_task(name="listing.check_for_spam")
def check_listing_for_spam(listing_id: int):
    """
    Tác vụ nền để gọi API AI và kiểm tra một tin đăng có phải là lừa đảo không.
    """
    SCAM_DETECTOR_API_URL = "https://dorangao-landify-scam-detector.hf.space/predict/"

    try:
        listing = Listing.objects.get(id=listing_id)
        logger.info(f"Bắt đầu kiểm tra scam bằng AI cho Listing ID: {listing_id}")

        soup = BeautifulSoup(listing.content, "html.parser")
        content_text = soup.get_text()
        payload = {
            "listing_id": str(listing.id),
            "title": listing.title,
            "content": content_text
        }

        try:
            response = requests.post(SCAM_DETECTOR_API_URL, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi gọi API AI cho Listing ID {listing_id}: {e}")
            return

        is_scam = result.get("is_scam", False)
        listing.scam_score = result.get("scam_score")
        listing.scam_detector_version = result.get("version")
        update_fields = ["scam_score", "scam_detector_version", "spam_check_status"]

        if is_scam:
            listing.active = False
            listing.spam_check_status = Listing.SpamCheckStatus.FLAGGED
            update_fields.append("active")
            logger.warning(f"SCAM ĐÃ ĐƯỢC PHÁT HIỆN bởi AI trong Listing ID: {listing_id}. Tin đã bị vô hiệu hóa.")

            reason = "Nội dung bị hệ thống AI nghi ngờ là lừa đảo."
            notify_user_of_listing_rejection.delay(listing_id=listing.id, reason=reason)
        else:
            listing.spam_check_status = Listing.SpamCheckStatus.CLEAN
            logger.info(f"Listing ID: {listing_id} được AI xác định là trong sạch.")

        listing.save(update_fields=update_fields)

    except Listing.DoesNotExist:
        logger.error(f"Task 'check_for_spam' thất bại: Listing với ID {listing_id} không tồn tại.")
    except Exception as e:
        logger.error(f"Lỗi không xác định (Task) khi kiểm tra scam cho Listing ID {listing_id}: {e}")