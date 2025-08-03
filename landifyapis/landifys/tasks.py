from celery import shared_task
from .models import Listing
from .models import User, Notification, NotificationCategory

SPAM_KEYWORDS = ['khuyến mãi sốc', 'vay tiền', 'tín dụng đen', 'casino', 'đánh bạc']

@shared_task
def check_listing_for_spam(listing_id):
    """
    Tác vụ nền để kiểm tra một bài đăng Listing có chứa nội dung spam hay không.
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        print(f"Bắt đầu kiểm tra spam cho Listing ID: {listing_id} - Tiêu đề: {listing.title}")

        # Logic kiểm tra spam rất đơn giản: tìm từ khóa
        is_spam_detected = False
        for keyword in SPAM_KEYWORDS:
            if keyword in listing.title.lower() or keyword in listing.content.lower():
                is_spam_detected = True
                break

        if is_spam_detected:
            # Nếu phát hiện spam, đánh dấu bài viết
            listing.active = False
            listing.save(update_fields=['active'])
            print(f"!!! SPAM ĐÃ ĐƯỢC PHÁT HIỆN trong Listing ID: {listing_id}")
        else:
            print(f"Listing ID: {listing_id} trong sạch.")

    except Listing.DoesNotExist:
        print(f"LỖI: Listing với ID {listing_id} không tồn tại.")


@shared_task
def notify_admins_of_new_protest(protest_id, protester_username, listing_title):
    """
    Tác vụ nền để gửi thông báo về kháng nghị mới đến tất cả các admin.
    """
    try:
        category, _ = NotificationCategory.objects.get_or_create(name='Kháng nghị mới')

        admins = User.objects.filter(role=User.Role.ADMIN)

        title = f"Kháng nghị mới cho tin đăng: {listing_title}"
        content = f"Người dùng '{protester_username}' đã gửi một kháng nghị (ID: {protest_id}) cho một báo cáo liên quan đến tin đăng của họ. Vui lòng xem xét."

        notifications_to_create = []
        for admin in admins:
            notifications_to_create.append(
                Notification(user=admin, category=category, title=title, content=content)
            )

        # Tạo tất cả thông báo trong một lần query để tăng hiệu suất
        Notification.objects.bulk_create(notifications_to_create)

        print(f"Đã gửi thông báo kháng nghị (ID: {protest_id}) đến {len(admins)} admin.")

    except Exception as e:
        print(f"Lỗi khi gửi thông báo kháng nghị: {e}")

@shared_task
def notify_user_of_protest_resolution(user_id, listing_title, protest_status, resolution_note):
    try:
        user = User.objects.get(id=user_id)
        category, _ = NotificationCategory.objects.get_or_create(name='Kết quả kháng nghị')

        title = f"Kháng nghị của bạn cho tin '{listing_title}' đã được xử lý"
        content = (
            f"Kết quả: {protest_status}.\n"
            f"Ghi chú từ quản trị viên: {resolution_note}"
        )

        Notification.objects.create(
            user=user,
            category=category,
            title=title,
            content=content
        )
        print(f"Đã gửi thông báo kết quả kháng nghị cho user ID: {user_id}")

    except User.DoesNotExist:
        print(f"LỖI: Không tìm thấy user ID {user_id} để gửi thông báo kết quả kháng nghị.")
    except Exception as e:
        print(f"Lỗi khi gửi thông báo kết quả kháng nghị: {e}")