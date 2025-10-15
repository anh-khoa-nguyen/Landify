# landifys/docs/moderation_docs.py

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.moderation.models import Protest, Report  # Import model để lấy choices
from apps.moderation.serializers import ProtestSerializer, ReportSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO REPORT VIEWSET
# ==============================================================================

report_viewset_schema = extend_schema_view(
    # Action: list (GET /api/reports/)
    list=extend_schema(
        summary="Lấy danh sách báo cáo",
        description=(
            "**Admin:** Xem tất cả các báo cáo trong hệ thống.\n"
            "**Người dùng thường:** Chỉ xem các báo cáo do chính mình tạo."
        ),
    ),
    # Action: retrieve (GET /api/reports/{id}/)
    retrieve=extend_schema(
        summary="Lấy chi tiết một báo cáo", description="Chỉ Admin hoặc người tạo báo cáo mới có thể xem chi tiết."
    ),
    # Action: create (POST /api/reports/)
    create=extend_schema(
        summary="Tạo một báo cáo vi phạm mới",
        description=(
            "Người dùng gửi một báo cáo về một đối tượng (tin đăng, người dùng, bài đăng, bình luận) vi phạm.\n"
            "**Lưu ý:** `reported_item_type` phải là một trong các giá trị: "
            f"`{', '.join([choice[0] for choice in Report.ItemType.choices])}`."
        ),
        examples=[
            OpenApiExample(
                "Ví dụ báo cáo một tin đăng",
                value={
                    "reported_item_type": "listing",
                    "reported_item_id": 45,
                    "description": "Tin đăng này chứa thông tin lừa đảo.",
                },
            )
        ],
    ),
    # Các action này chỉ dành cho Admin
    update=extend_schema(summary="[Admin] Cập nhật một báo cáo"),
    partial_update=extend_schema(summary="[Admin] Cập nhật một phần báo cáo"),
    destroy=extend_schema(summary="[Admin] Xóa một báo cáo"),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO PROTEST VIEWSET
# ==============================================================================

protest_viewset_schema = extend_schema_view(
    # Các action CRUD mặc định chỉ dành cho Admin
    list=extend_schema(summary="[Admin] Lấy danh sách tất cả kháng nghị"),
    retrieve=extend_schema(summary="[Admin] Lấy chi tiết một kháng nghị"),
    create=extend_schema(
        summary="[Admin] Tạo một kháng nghị (thường không dùng)",
        description="Endpoint này tồn tại do kế thừa từ ModelViewSet, nhưng luồng chính để tạo kháng nghị là từ `POST /api/listings/{public_id}/protest/`.",
    ),
    update=extend_schema(summary="[Admin] Cập nhật một kháng nghị"),
    partial_update=extend_schema(summary="[Admin] Cập nhật một phần kháng nghị"),
    destroy=extend_schema(summary="[Admin] Xóa một kháng nghị"),
)

# Schema cho action tùy chỉnh `resolve`
resolve_protest_schema = extend_schema(
    summary="[Admin] Xử lý một kháng nghị",
    description=(
        "Quản trị viên đưa ra quyết định cuối cùng cho một kháng nghị.\n"
        "- Nếu `status` là `RESOLVED`, tin đăng liên quan sẽ được kích hoạt lại.\n"
        "- Nếu `status` là `REJECTED`, tin đăng vẫn sẽ không hoạt động."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Trạng thái xử lý mới",
                    "enum": [Protest.Status.RESOLVED, Protest.Status.REJECTED],
                },
                "resolution_note": {"type": "string", "description": "Ghi chú của admin giải thích về quyết định."},
            },
            "required": ["status", "resolution_note"],
        }
    },
    responses={
        200: ProtestSerializer,
        400: {"description": "Trạng thái không hợp lệ hoặc kháng nghị đã được xử lý trước đó."},
    },
)
