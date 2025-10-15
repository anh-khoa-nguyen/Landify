# landifys/docs/utilities_docs.py

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view

# Import serializers để mô tả request/response
from apps.interactions.serializers import ReviewSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO PROPERTY ANALYSIS VIEWSET
# ==============================================================================

property_analysis_viewset_schema = extend_schema_view(
    # Action: feng_shui_analysis (POST /api/analysis/{pk}/feng-shui/)
    feng_shui_analysis=extend_schema(
        summary="Phân tích phong thủy cho BĐS",
        description=(
            "Phân tích sự tương hợp giữa hướng của bất động sản và mệnh của người dùng dựa trên ngày sinh. "
            "Kết quả trả về bao gồm mệnh của người dùng, hướng nhà, điểm tương hợp và một đoạn văn phân tích chi tiết."
        ),
        parameters=[
            OpenApiParameter(
                "pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của Bất động sản cần phân tích"
            )
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "date_of_birth": {
                        "type": "string",
                        "format": "date",
                        "description": "Ngày sinh theo định dạng YYYY-MM-DD",
                    }
                },
                "required": ["date_of_birth"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "user_menh_element": {"type": "string"},
                    "property_direction": {"type": "string"},
                    "compatibility_score": {"type": "integer"},
                    "analysis": {"type": "string"},
                },
            },
            400: {"description": "Ngày sinh không hợp lệ hoặc BĐS thiếu thông tin về hướng."},
        },
        examples=[OpenApiExample("Ví dụ", value={"date_of_birth": "1990-08-15"})],
    ),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO AGORA TOKEN VIEWSET
# ==============================================================================

agora_token_viewset_schema = extend_schema_view(
    # Action: generate_token (POST /api/agora/generate/)
    generate_token=extend_schema(
        summary="Tạo Agora Token cho cuộc gọi video",
        description=(
            "Tạo một token truy cập tạm thời cho người dùng hiện tại để tham gia vào một kênh gọi video của Agora. "
            "Token này có hiệu lực trong 1 giờ."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {"channelName": {"type": "string", "description": "Tên của kênh (phòng) video call"}},
                "required": ["channelName"],
            }
        },
        responses={
            200: {"type": "object", "properties": {"token": {"type": "string"}, "uid": {"type": "integer"}}},
            400: {"description": "`channelName` là bắt buộc."},
        },
        examples=[OpenApiExample("Ví dụ", value={"channelName": "video-call-room-123"})],
    )
)
