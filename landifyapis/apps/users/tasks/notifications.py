# D:\Backend\Landify\landifyapis\apps\users\tasks\notifications.py

from celery import shared_task
import logging

# <<< THAY ĐỔI IMPORT: Dùng đường dẫn tuyệt đối từ gốc project >>>
from apps.users.models import User
from apps.listings.models import Listing
from apps.common.utils import firebase

logger = logging.getLogger(__name__)


@shared_task(name="notifications.notify_followers_of_new_listing")
def notify_followers_of_new_listing(owner_id: int, listing_id: int):
    """
    Tác vụ nền để thông báo cho tất cả người theo dõi khi một người dùng đăng tin mới.
    """
    logger.info(f"Bắt đầu gửi thông báo cho người theo dõi của user ID {owner_id} về listing ID {listing_id}.")
    try:
        owner = User.objects.get(pk=owner_id)
        listing = Listing.objects.get(pk=listing_id)

        subscriptions = owner.follower_set.select_related('follower').all()

        if not subscriptions.exists():
            logger.info(f"User ID {owner_id} không có người theo dõi nào. Kết thúc tác vụ.")
            return

        owner_name = owner.get_full_name() or owner.username
        title = f"{owner_name} vừa đăng tin mới"
        content = f"Hãy xem ngay tin đăng bất động sản mới: \"{listing.title}\""

        # Tạo public_id từ listing.id
        from apps.common.utils.hashids import hashids
        public_id = hashids.encode(listing.id)

        related_item = {
            "type": "listing",
            "public_id": public_id
        }

        followers_notified_count = 0
        for sub in subscriptions:
            follower = sub.follower
            firebase.send_firestore_notification(
                user_id=follower.id,
                category="new_listing_from_followed_user",
                title=title,
                content=content,
                related_item=related_item
            )
            followers_notified_count += 1

        logger.info(f"Đã gửi thành công thông báo đến {followers_notified_count} người theo dõi.")

    except User.DoesNotExist:
        logger.error(f"Lỗi (Task): User với ID {owner_id} không tồn tại.")
    except Listing.DoesNotExist:
        logger.error(f"Lỗi (Task): Listing với ID {listing_id} không tồn tại.")
    except Exception as e:
        logger.error(f"Lỗi không xác định trong tác vụ notify_followers_of_new_listing: {e}", exc_info=True)