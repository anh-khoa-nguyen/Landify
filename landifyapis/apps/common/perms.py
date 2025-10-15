from rest_framework import permissions

from apps.users.models import User


class IsAdmin(permissions.BasePermission):
    """
    Chỉ cho phép truy cập nếu người dùng đã được xác thực và có vai trò là ADMIN.
    """

    message = "Bạn phải là Quản trị viên để thực hiện hành động này."

    def has_permission(self, request, view):
        # Người dùng phải đăng nhập và có vai trò là admin
        return request.user.is_authenticated and request.user.is_superuser


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Cho phép mọi người truy cập cho các request an toàn (GET, HEAD, OPTIONS).
    Đối với các request khác (POST, PUT, PATCH, DELETE), chỉ cho phép nếu người dùng là admin.
    """

    message = "Bạn phải là Quản trị viên để chỉnh sửa đối tượng này."

    def has_permission(self, request, view):
        # Cho phép đọc cho tất cả mọi người
        if request.method in permissions.SAFE_METHODS:
            return True

        # Quyền ghi chỉ dành cho admin
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Kiểm tra quyền trên một đối tượng cụ thể (object-level permission).
    Cho phép truy cập nếu người dùng là admin, hoặc nếu họ là chủ sở hữu của đối tượng.
    """

    message = "Bạn không có quyền thực hiện hành động này trên đối tượng này."

    def has_object_permission(self, request, view, obj):
        # Admin luôn có quyền truy cập
        if request.user.is_authenticated and request.user.role == User.Role.ADMIN:
            return True

        owner_fields = ["user", "owner", "reporter", "protester", "follower"]
        for field in owner_fields:
            if hasattr(obj, field) and getattr(obj, field) == request.user:
                return True

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Một phiên bản phổ biến khác: cho phép mọi người đọc, nhưng chỉ chủ sở hữu
    mới có quyền chỉnh sửa. Admin không có quyền đặc biệt ở đây.
    """

    message = "Bạn không phải là chủ sở hữu của đối tượng này."

    def has_object_permission(self, request, view, obj):
        # Cho phép đọc cho tất cả mọi người
        if request.method in permissions.SAFE_METHODS:
            return True

        # Quyền ghi chỉ dành cho chủ sở hữu
        owner_fields = ["user", "owner"]
        for field in owner_fields:
            if hasattr(obj, field) and getattr(obj, field) == request.user:
                return True

        return False


class IsIdentityVerified(permissions.BasePermission):
    """
    Chỉ cho phép truy cập nếu người dùng đã hoàn tất xác minh danh tính (eKYC).
    Đây là cấp độ xác thực cao nhất.
    """

    message = "Bạn cần hoàn tất xác minh danh tính (eKYC) để thực hiện hành động này."

    def has_permission(self, request, view):
        # Người dùng phải đăng nhập và cờ is_identity_verified phải là True
        return (
            request.user.is_authenticated
            and request.user.is_identity_verified
            and request.user.is_id_card_verified is True
        )
