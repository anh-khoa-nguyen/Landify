# landifys/docs/accounts_docs.py

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.users.serializers import UserCreateSerializer, UserSerializer, UserUpdateSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO AUTH VIEWSET
# ==============================================================================

auth_viewset_schema = extend_schema_view(
    # Action: connect_firebase_user (POST /api/auth/connect/)
    connect_firebase_user=extend_schema(
        summary="Xác nhận kết nối người dùng Firebase",
        description=(
            "Endpoint này được gọi sau khi người dùng đăng nhập thành công bằng Firebase ở phía client. "
            "Client gửi Firebase ID Token trong header `Authorization: Bearer <token>`. "
            "Nếu token hợp lệ, server sẽ trả về thông tin người dùng tương ứng trong database."
        ),
        responses={200: UserSerializer},
    )
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO USER VIEWSET
# ==============================================================================

user_viewset_schema = extend_schema_view(
    # Action: list (GET /api/users/)
    list=extend_schema(
        summary="Lấy danh sách người dùng",
        description="Trả về danh sách các người dùng đang hoạt động trong hệ thống, đã được phân trang.",
    ),
    # Action: retrieve (GET /api/users/{id}/)
    retrieve=extend_schema(
        summary="Lấy thông tin chi tiết của một người dùng",
        description="Lấy thông tin công khai của một người dùng cụ thể bằng ID của họ.",
    ),
    # Action: create (POST /api/users/)
    create=extend_schema(
        summary="Đăng ký tài khoản người dùng mới",
        description="Tạo một tài khoản người dùng mới với các thông tin cơ bản. Mật khẩu sẽ được hash an toàn.",
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        examples=[
            OpenApiExample(
                "Ví dụ đăng ký",
                value={
                    "username": "nguyenvana",
                    "password": "a_strong_password_123",
                    "first_name": "An",
                    "last_name": "Nguyễn Văn",
                    "phone_number": "0987654321",
                },
            )
        ],
    ),
    # Action: update & partial_update (PUT, PATCH /api/users/{id}/)
    update=extend_schema(summary="[Admin] Cập nhật toàn bộ thông tin người dùng"),
    partial_update=extend_schema(summary="[Admin] Cập nhật một phần thông tin người dùng"),
    # Action: destroy (DELETE /api/users/{id}/)
    destroy=extend_schema(
        summary="[Admin] Xóa vĩnh viễn một người dùng",
        description="Hành động này sẽ xóa người dùng khỏi CSDL và không thể hoàn tác. Để vô hiệu hóa, hãy dùng endpoint `disable`.",
    ),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO CÁC ACTION TÙY CHỈNH CỦA USER VIEWSET
# ==============================================================================

# Action: current_user (GET /api/users/current-user/)
current_user_schema = extend_schema(
    summary="Lấy thông tin người dùng đang đăng nhập",
    description="Một shortcut tiện lợi để client lấy thông tin của chính mình mà không cần biết ID.",
    responses={200: UserSerializer},
)

# Action: complete_profile (PATCH /api/users/complete-profile/)
complete_profile_schema = extend_schema(
    summary="Người dùng tự cập nhật hồ sơ",
    description="Cho phép người dùng đang đăng nhập cập nhật các thông tin cá nhân cơ bản của họ (tên, email).",
    request=UserUpdateSerializer,
    responses={200: UserSerializer},
)

# Action: change_avatar (PATCH /api/users/change-avatar/)
change_avatar_schema = extend_schema(
    summary="Thay đổi ảnh đại diện",
    description="Tải lên file ảnh mới để cập nhật avatar. Request phải ở dạng `multipart/form-data`.",
    request={
        "multipart/form-data": {"type": "object", "properties": {"avatar": {"type": "string", "format": "binary"}}}
    },
    responses={
        200: {"type": "object", "properties": {"avatar_url": {"type": "string", "format": "uri"}}},
        400: {"description": "Không có file nào được cung cấp."},
    },
)

# Action: toggle_follow (POST /api/users/{id}/follow/)
toggle_follow_schema = extend_schema(
    summary="Theo dõi hoặc bỏ theo dõi người dùng",
    description="Thực hiện hành động theo dõi (nếu chưa theo dõi) hoặc bỏ theo dõi (nếu đã theo dõi) một người dùng khác.",
    request=None,  # Không có request body
    responses={
        201: {"description": "Theo dõi thành công."},
        204: {"description": "Bỏ theo dõi thành công (Không có nội dung trả về)."},
        400: {"description": "Người dùng không thể tự theo dõi chính mình."},
    },
)

# Action: disable_account (PATCH /api/users/{id}/disable/)
disable_account_schema = extend_schema(
    summary="[Admin] Vô hiệu hóa/Kích hoạt tài khoản",
    description="Chỉ dành cho Quản trị viên. Chuyển đổi trạng thái `is_active` của một tài khoản người dùng.",
    request=None,  # Không có request body
    responses={
        200: {"type": "object", "properties": {"message": {"type": "string"}}},
        403: {"description": "Không có quyền thực hiện hành động này."},
    },
)
