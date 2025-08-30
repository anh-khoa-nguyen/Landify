from celery import shared_task

# Import client Firestore và các hằng số cần thiết
from .utils import db
from firebase_admin import firestore

# Hằng số này không thay đổi vì nó là logic nghiệp vụ thuần túy
SPAM_KEYWORDS = ['khuyến mãi sốc', 'vay tiền', 'tín dụng đen', 'casino', 'đánh bạc']


# =============================================================================
# LƯU Ý QUAN TRỌNG VỀ KIẾN TRÚC MỚI:
#
# Các tác vụ Celery này giờ đây tương tác trực tiếp với Firestore thay vì
# cơ sở dữ liệu SQL thông qua Django ORM.
#
# - `Model.objects.get()` được thay thế bằng `db.collection(...).document(...).get()`.
# - `Model.objects.filter()` được thay thế bằng `db.collection(...).where(...)`.
# - `instance.save()` được thay thế bằng `.update()` hoặc `.set()`.
# - `Model.objects.bulk_create()` được thay thế bằng Batched Writes (`db.batch()`).
# =============================================================================


@shared_task
def check_listing_for_spam(listing_id):
    """
    Tác vụ nền để kiểm tra một tin đăng (Listing) trong Firestore
    có chứa nội dung spam hay không.
    """
    try:
        # 1. THAY THẾ ORM: Lấy document từ Firestore thay vì object từ DB
        listing_ref = db.collection('listings').document(listing_id)
        listing_doc = listing_ref.get()

        if not listing_doc.exists:
            print(f"LỖI: Listing với ID {listing_id} không tồn tại trong Firestore.")
            return

        print(f"Bắt đầu kiểm tra spam cho Listing ID: {listing_id}")
        listing_data = listing_doc.to_dict()

        # 2. LOGIC NGHIỆP VỤ: Giữ nguyên
        is_spam_detected = False
        # Dùng .get() để tránh lỗi nếu trường không tồn tại
        title = listing_data.get('title', '').lower()
        content = listing_data.get('content', '').lower()

        for keyword in SPAM_KEYWORDS:
            if keyword in title or keyword in content:
                is_spam_detected = True
                break

        if is_spam_detected:
            # 3. THAY THẾ ORM: Cập nhật document trong Firestore
            listing_ref.update({'active': False, 'spam_check_status': 'flagged'})
            print(f"!!! SPAM ĐÃ ĐƯỢC PHÁT HIỆN trong Listing ID: {listing_id}. Tin đã bị vô hiệu hóa.")
        else:
            listing_ref.update({'spam_check_status': 'clean'})
            print(f"Listing ID: {listing_id} trong sạch.")

    except Exception as e:
        print(f"LỖI không xác định khi kiểm tra spam cho Listing ID {listing_id}: {e}")


@shared_task
def notify_admins_of_new_protest(protest_id, protester_username, listing_title):
    """
    Tác vụ nền để gửi thông báo về kháng nghị mới đến tất cả các admin.
    Sử dụng Batched Writes để tạo thông báo hiệu quả.
    """
    try:
        # 1. THAY THẾ ORM: Query tất cả user có vai trò 'admin'
        admins_query = db.collection('users').where('role', '==', 'admin').stream()

        admin_ids = [admin.id for admin in admins_query]

        if not admin_ids:
            print("Không tìm thấy admin nào để gửi thông báo.")
            return

        # 2. Chuẩn bị nội dung thông báo
        title = f"Kháng nghị mới cho tin đăng: {listing_title}"
        content = f"Người dùng '{protester_username}' đã gửi một kháng nghị (ID: {protest_id}). Vui lòng xem xét."

        # 3. THAY THẾ ORM (bulk_create): Sử dụng Batched Writes của Firestore
        batch = db.batch()

        for admin_id in admin_ids:
            # Tạo một tham chiếu cho document thông báo mới với ID tự động
            notification_ref = db.collection('notifications').document()

            notification_data = {
                'user_id': admin_id,
                'category': 'new_protest',
                'title': title,
                'content': content,
                'is_read': False,
                'created_at': firestore.SERVER_TIMESTAMP,
                'related_item': {'type': 'protest', 'id': protest_id}
            }
            # Thêm thao tác 'set' vào batch
            batch.set(notification_ref, notification_data)

        # Gửi tất cả các thao tác ghi lên server trong một lần
        batch.commit()

        print(f"Đã gửi thông báo kháng nghị (ID: {protest_id}) đến {len(admin_ids)} admin.")

    except Exception as e:
        print(f"Lỗi khi gửi thông báo kháng nghị: {e}")


@shared_task
def notify_user_of_protest_resolution(user_id, listing_title, protest_status, resolution_note):
    """
    Tác vụ nền để gửi thông báo về kết quả xử lý kháng nghị cho người dùng.
    """
    try:
        # 1. Chuẩn bị nội dung thông báo
        title = f"Kháng nghị của bạn cho tin '{listing_title}' đã được xử lý"
        content = (
            f"Kết quả: {protest_status}.\n"
            f"Ghi chú từ quản trị viên: {resolution_note}"
        )

        notification_data = {
            'user_id': user_id,
            'category': 'protest_resolution',
            'title': title,
            'content': content,
            'is_read': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        # 2. THAY THẾ ORM (create): Thêm một document mới vào collection 'notifications'
        db.collection('notifications').add(notification_data)

        print(f"Đã gửi thông báo kết quả kháng nghị cho user ID: {user_id}")

    except Exception as e:
        # Không cần kiểm tra User.DoesNotExist vì chúng ta không đọc từ collection 'users'
        print(f"Lỗi khi gửi thông báo kết quả kháng nghị cho user ID {user_id}: {e}")