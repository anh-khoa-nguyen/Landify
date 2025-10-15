# landifys/docs/listings_docs.py

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view

# Import các serializer cần thiết để mô tả request/response
from apps.listings.serializers import ListingCreateSerializer, ListingDetailSerializer
from apps.moderation.serializers import ProtestSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO LISTING VIEWSET
# ==============================================================================

listing_viewset_schema = extend_schema_view(
    # Action: list (GET /api/listings/)
    list=extend_schema(
        summary="Lấy danh sách các tin đăng",
        description="Trả về một danh sách các tin đăng đang hoạt động và có sẵn, đã được phân trang.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Từ khóa tìm kiếm chung trong tiêu đề, nội dung, địa chỉ.",
            ),
            # Các tham số phân trang (page, page_size) sẽ được drf-spectacular tự động thêm vào
        ],
    ),
    # Action: retrieve (GET /api/listings/{public_id}/)
    retrieve=extend_schema(
        summary="Lấy chi tiết một tin đăng",
        description="Lấy thông tin chi tiết của một tin đăng bằng `public_id` của nó.",
        responses={200: ListingDetailSerializer},
    ),
    # Action: create (POST /api/listings/)
    create=extend_schema(
        summary="Tạo một tin đăng mới",
        description=(
            "Tạo một tin đăng mới. Cần phải cung cấp `property` (để tạo mới BĐS) "
            "hoặc `property_id` (để liên kết BĐS đã có), nhưng không phải cả hai."
        ),
        request=ListingCreateSerializer,  # Tự động suy luận từ serializer
        responses={201: ListingDetailSerializer},
        examples=[
            OpenApiExample(
                "Ví dụ 1: Tạo tin đăng kèm BĐS mới",
                summary="Tạo tin bán căn hộ và tạo luôn đối tượng BĐS",
                value={
                    "listing_type": 1,
                    "title": "Bán gấp căn hộ chung cư 2PN tại The Sun Avenue",
                    "content": "<p>Nội dung chi tiết...</p>",
                    "price_value": 3500000000,
                    "unit_price": 2,  # Giả sử ID 2 là "tỷ"
                    "property": {
                        "property_type_id": 1,  # Giả sử ID 1 là "Căn hộ"
                        "location": {"street": "28 Mai Chí Thọ", "ward_id": 99, "district_id": 9, "city_id": 1},
                        "area": 75.5,
                        "direction_id": 5,  # Giả sử ID 5 là "Đông Nam"
                    },
                },
            ),
            OpenApiExample(
                "Ví dụ 2: Tạo tin đăng cho BĐS đã có",
                summary="Tạo tin cho thuê cho một BĐS đã tồn tại trong hệ thống",
                value={
                    "listing_type": 2,  # Giả sử ID 2 là "Cho thuê"
                    "title": "Cho thuê nhà nguyên căn mặt tiền",
                    "content": "<p>Nội dung chi tiết...</p>",
                    "price_value": 25000000,
                    "unit_price": 5,  # Giả sử ID 5 là "triệu/tháng"
                    "property_id": 123,  # ID của BĐS đã có
                },
            ),
        ],
    ),
    # Action: update (PUT /api/listings/{public_id}/)
    update=extend_schema(
        summary="Cập nhật toàn bộ tin đăng",
        description="Cập nhật toàn bộ thông tin của một tin đăng. Yêu cầu tất cả các trường.",
        request=ListingCreateSerializer,
        responses={200: ListingDetailSerializer},
    ),
    # Action: partial_update (PATCH /api/listings/{public_id}/)
    partial_update=extend_schema(
        summary="Cập nhật một phần tin đăng",
        description="Cập nhật một hoặc nhiều trường thông tin của một tin đăng.",
        request=ListingCreateSerializer,
        responses={200: ListingDetailSerializer},
    ),
    # Action: destroy (DELETE /api/listings/{public_id}/)
    destroy=extend_schema(
        summary="Xóa một tin đăng",
        description="Lưu ý: Đây là hành động 'soft delete', chỉ đánh dấu tin đăng là không hoạt động (`active=False`).",
    ),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO CÁC ACTION TÙY CHỈNH
# ==============================================================================

# Action: update_features (PATCH /api/listings/{public_id}/update-features/)
update_features_schema = extend_schema(
    summary="Cập nhật các đặc điểm cho tin đăng",
    description="Thêm, sửa hoặc xóa các cặp (đặc điểm - giá trị) cho một tin đăng. Gửi một danh sách các đặc điểm muốn cập nhật.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "features": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "feature_id": {"type": "integer", "description": "ID của đặc điểm"},
                            "value": {"type": "string", "description": "Giá trị tương ứng (số, chuỗi, boolean...)"},
                        },
                    },
                }
            },
        }
    },
    responses={200: ListingDetailSerializer, 400: {"description": "Dữ liệu gửi lên không hợp lệ."}},
    examples=[
        OpenApiExample(
            "Ví dụ",
            summary="Cập nhật số phòng ngủ và hướng ban công",
            value={
                "features": [
                    {"feature_id": 5, "value": 3},  # Cập nhật "Số phòng ngủ" = 3
                    {"feature_id": 2, "value": "Đông Nam"},  # Cập nhật "Hướng ban công" = "Đông Nam"
                ]
            },
        )
    ],
)

# Action: search (GET /api/listings/search/)
search_listings_schema = extend_schema(
    summary="Tìm kiếm tin đăng",
    description="Tìm kiếm tin đăng dựa trên từ khóa. API sẽ trả về kết quả đã phân trang.",
    parameters=[
        OpenApiParameter(
            name="q",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Từ khóa tìm kiếm.",
            required=True,
        )
    ],
    responses={200: ListingDetailSerializer(many=True)},
)

# Action: protest (POST /api/listings/{public_id}/protest/)
protest_listing_schema = extend_schema(
    summary="Gửi kháng nghị cho tin đăng",
    description="Cho phép người dùng gửi kháng nghị khi tin đăng của họ bị từ chối hoặc gỡ bỏ. Chỉ áp dụng cho các tin đăng không hoạt động.",
    request=ProtestSerializer,
    responses={
        201: ProtestSerializer,
        400: {"description": "Không thể kháng nghị tin đăng đang hoạt động hoặc đã có kháng nghị đang chờ xử lý."},
    },
)
