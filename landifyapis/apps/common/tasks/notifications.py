# apps/common/tasks/notifications.py
from celery import shared_task
from apps.users.models import User
from ..utils import firebase
import logging

logger = logging.getLogger(__name__)

# === TÁC VỤ TỔNG QUÁT MỚI: Gửi thông báo cho MỘT người dùng ===
@shared_task(name="notifications.send_to_user")
def send_notification_to_user(user_id: int, category: str, title: str, content: str, related_item: dict = None):
    """
    Tác vụ nền tổng quát để gửi một thông báo Firestore đến một người dùng cụ thể.
    """
    try:
        firebase.send_firestore_notification(
            user_id=user_id,
            category=category,
            title=title,
            content=content,
            related_item=related_item
        )
        logger.info(f"Đã gửi yêu cầu thông báo (category: {category}) đến user ID: {user_id}")
    except Exception as e:
        logger.error(f"Lỗi (Task) khi gửi thông báo cho user ID {user_id}: {e}")


# === TÁC VỤ TỔNG QUÁT MỚI: Gửi thông báo cho TẤT CẢ admin ===
@shared_task(name="notifications.send_to_admins")
def send_notification_to_admins(category: str, title: str, content: str, related_item: dict = None):
    """
    Tác vụ nền tổng quát để gửi cùng một thông báo đến tất cả các admin đang hoạt động.
    """
    try:
        admin_users = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        if not admin_users.exists():
            logger.warning("Không tìm thấy admin nào để gửi thông báo.")
            return

        for admin in admin_users:
            # Gọi hàm gửi thông báo cấp thấp cho từng admin
            firebase.send_firestore_notification(
                user_id=admin.id,
                category=category,
                title=title,
                content=content,
                related_item=related_item
            )

        logger.info(f"Đã gửi yêu cầu thông báo (category: {category}) đến {admin_users.count()} admin.")
    except Exception as e:
        logger.error(f"Lỗi (Task) khi gửi thông báo hàng loạt cho admin: {e}")

# Các tác vụ cũ (notify_admins_of_new_protest và notify_user_of_protest_resolution)
# bây giờ đã có thể xóa đi vì chúng ta đã có các phiên bản tổng quát hơn.