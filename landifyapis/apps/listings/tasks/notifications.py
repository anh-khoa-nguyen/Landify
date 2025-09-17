# apps/listings/tasks/notifications.py
from celery import shared_task
import logging

from apps.listings.models import Listing
from apps.common.utils import firebase
from apps.common.utils.hashids import hashids

logger = logging.getLogger(__name__)


@shared_task(name="listings.notify_user_of_rejection")
def notify_user_of_listing_rejection(listing_id: int, reason: str):
    """
    Tác vụ nền để gửi thông báo Firestore đến người dùng khi tin đăng của họ bị từ chối/gỡ.
    """
    logger.info(f"Bắt đầu gửi thông báo từ chối cho chủ sở hữu của Listing ID {listing_id}.")
    try:
        listing = Listing.objects.select_related('user').get(pk=listing_id)
        owner = listing.user

        title = "Tin đăng của bạn đã bị tạm ẩn"
        content = f"Tin đăng \"{listing.title}\" đã bị tạm ẩn vì lý do: {reason}. Bạn có thể kháng nghị nếu cho rằng đây là một sai sót."

        public_id = hashids.encode(listing.id)
        related_item = {
            "type": "listing",
            "public_id": public_id
        }

        firebase.send_firestore_notification(
            user_id=owner.id,
            category="listing_moderation",
            title=title,
            content=content,
            related_item=related_item
        )

        logger.info(f"Đã gửi thành công thông báo từ chối cho User ID {owner.id}.")

    except Listing.DoesNotExist:
        logger.error(f"Lỗi (Task): Không thể gửi thông báo vì Listing với ID {listing_id} không tồn tại.")
    except Exception as e:
        logger.error(f"Lỗi không xác định trong tác vụ notify_user_of_listing_rejection: {e}", exc_info=True)