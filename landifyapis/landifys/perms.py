from rest_framework import permissions

# Import client Firestore đã được khởi tạo từ một file tập trung (ví dụ: utils.py)
# Điều này đảm bảo chúng ta sử dụng cùng một instance của client ở mọi nơi.
from .utils import db


# =============================================================================
# LƯU Ý QUAN TRỌNG VỀ KIẾN TRÚC MỚI:
#
# 1. Nguồn Dữ Liệu: Các lớp permission này không còn làm việc với Django Models
#    hay đối tượng `request.user` nữa. Chúng hoạt động dựa trên:
#    - `request.firebase_user`: Một dictionary chứa payload từ Firebase ID token.
#    - Firestore Database: Thực hiện các truy vấn đọc để lấy thông tin chi tiết
#      như vai trò (role) hoặc trạng thái xác minh.
#
# 2. Hiệu Năng: Mỗi lần kiểm tra quyền (ví dụ: kiểm tra vai trò admin) sẽ
#    tốn một lượt đọc từ Firestore. Trong môi trường production, cần cân nhắc
#    các chiến lược caching để giảm thiểu số lượt đọc này.
#
# 3. `obj`: Tham số `obj` trong `has_object_permission` giờ đây là một
#    dictionary, không phải là một đối tượng model.
# =============================================================================


def _is_admin(request):
    """
    Hàm helper để kiểm tra xem người dùng hiện tại có phải là admin hay không.
    Giảm thiểu việc lặp lại code truy vấn Firestore.
    """
    # Kiểm tra xem người dùng đã được xác thực bởi FirebaseAuthentication chưa
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return False

    uid = request.firebase_user.get('uid')
    if not uid:
        return False

    try:
        # Thực hiện một truy vấn đọc tới Firestore để lấy vai trò của người dùng
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            # Trả về True nếu trường 'role' trong document là 'admin'
            return user_doc.to_dict().get('role') == 'admin'
        return False
    except Exception as e:
        # Trong ứng dụng thực tế, bạn nên log lỗi này
        print(f"Lỗi khi kiểm tra quyền admin cho UID {uid}: {e}")
        return False

class IsFirebaseAuthenticated(permissions.BasePermission):
    """
    Cho phép truy cập chỉ khi người dùng đã được xác thực thành công
    bởi FirebaseAuthentication (tức là request.firebase_user tồn tại).
    """
    message = "Yêu cầu xác thực không hợp lệ hoặc thiếu."

    def has_permission(self, request, view):
        return hasattr(request, 'firebase_user') and request.firebase_user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Cho phép truy cập không giới hạn cho các request an toàn (GET, HEAD, OPTIONS).
    Đối với các request khác, chỉ cho phép nếu người dùng là admin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Đối với các phương thức không an toàn (POST, PUT, PATCH, DELETE),
        # chỉ admin mới có quyền.
        return _is_admin(request)


class IsAdminOrForbidden(permissions.BasePermission):
    """
    Chỉ cho phép truy cập nếu người dùng được xác thực và có vai trò là admin.
    Nếu không, truy cập sẽ bị cấm hoàn toàn.
    """

    def has_permission(self, request, view):
        return _is_admin(request)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Kiểm tra quyền trên một đối tượng cụ thể.
    Cho phép truy cập nếu người dùng là admin, hoặc nếu họ là chủ sở hữu của đối tượng.
    """
    message = "Bạn không có quyền thực hiện hành động này trên đối tượng này."

    def has_object_permission(self, request, view, obj):
        # `obj` ở đây là một dictionary từ Firestore.

        # 1. Luôn cho phép nếu người dùng là admin
        if _is_admin(request):
            return True

        # 2. Nếu không phải admin, kiểm tra quyền sở hữu
        if not hasattr(request, 'firebase_user') or not request.firebase_user:
            return False  # Người dùng chưa xác thực

        current_user_uid = request.firebase_user.get('uid')

        # Giả định rằng document trong Firestore có một trường là 'user_id'
        # hoặc 'owner_id' để xác định chủ sở hữu.
        owner_uid = obj.get('user_id')

        if not owner_uid:
            # Nếu đối tượng không có thông tin chủ sở hữu, từ chối quyền để đảm bảo an toàn.
            return False

        return owner_uid == current_user_uid


class IsIdentityVerified(permissions.BasePermission):
    """
    Chỉ cho phép truy cập nếu người dùng đã hoàn tất xác minh danh tính và SĐT.
    """
    message = 'Tài khoản của bạn phải được xác minh số điện thoại và danh tính (eKYC) để thực hiện hành động này.'

    def has_permission(self, request, view):
        if not hasattr(request, 'firebase_user') or not request.firebase_user:
            return False

        uid = request.firebase_user.get('uid')
        if not uid:
            return False

        try:
            # Truy vấn Firestore để lấy trạng thái xác minh
            user_doc = db.collection('users').document(uid).get()

            if not user_doc.exists:
                return False

            user_data = user_doc.to_dict()

            # Kiểm tra cả hai trường boolean
            is_phone_verified = user_data.get('is_phone_verified', False)
            is_id_card_verified = user_data.get('is_id_card_verified', False)

            return is_phone_verified and is_id_card_verified

        except Exception as e:
            print(f"Lỗi khi kiểm tra trạng thái xác minh cho UID {uid}: {e}")
            return False