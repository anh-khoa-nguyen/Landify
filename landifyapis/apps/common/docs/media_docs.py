# landifys/docs/media_docs.py

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from apps.properties.serializers import PropertyMediaSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO MEDIA VIEWSET
# ==============================================================================
# Vì đây là một ViewSet lồng nhau, chúng ta cần thêm tham số `property_pk` vào hầu hết các endpoint.

media_viewset_schema = extend_schema_view(
    # Action: list (GET /api/properties/{property_pk}/media/)
    list=extend_schema(
        summary="Lấy danh sách media của một BĐS",
        description="Trả về danh sách tất cả ảnh/video thuộc về một bất động sản cụ thể.",
        parameters=[
            OpenApiParameter(
                name="property_pk",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID của Bất động sản cha.",
            )
        ],
    ),
    # Action: retrieve (GET /api/properties/{property_pk}/media/{id}/)
    retrieve=extend_schema(
        summary="Lấy chi tiết một media",
        description="Lấy thông tin chi tiết của một đối tượng media (ảnh/video) bằng ID của nó.",
        parameters=[
            OpenApiParameter(
                name="property_pk",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID của Bất động sản cha.",
            ),
            OpenApiParameter(
                name="id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH, description="ID của đối tượng Media."
            ),
        ],
    ),
    # Action: create (POST /api/properties/{property_pk}/media/)
    create=extend_schema(
        summary="Tải lên media mới cho BĐS",
        description="Tải lên một file ảnh hoặc video và liên kết nó với một bất động sản. Request phải ở dạng `multipart/form-data`.",
        parameters=[
            OpenApiParameter(
                name="property_pk",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID của Bất động sản cha.",
            )
        ],
        # Rất quan trọng: Mô tả request body cho việc upload file
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",  # Báo cho Swagger UI đây là một trường để upload file
                    }
                },
            }
        },
        responses={
            201: {
                "description": "Tải lên thành công.",
                "content": {
                    "application/json": {"schema": {"type": "object", "properties": {"message": {"type": "string"}}}}
                },
            },
            400: {"description": "Không có file nào được cung cấp."},
            403: {"description": "Không có quyền thực hiện hành động này trên BĐS."},
        },
    ),
    # Action: destroy (DELETE /api/properties/{property_pk}/media/{id}/)
    destroy=extend_schema(
        summary="Xóa một media",
        description="Xóa một đối tượng media khỏi bất động sản và đồng thời xóa file trên Cloudinary.",
        parameters=[
            OpenApiParameter(
                name="property_pk",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID của Bất động sản cha.",
            ),
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID của đối tượng Media cần xóa.",
            ),
        ],
    ),
)
