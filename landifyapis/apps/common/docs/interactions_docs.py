# landifys/docs/interactions_docs.py

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

# Import serializers để mô tả request/response
from apps.interactions.serializers import WishlistSerializer, AppointmentSerializer, ReviewSerializer
from apps.social.serializers import PostSerializer, CommentSerializer, ReactionSerializer
from apps.interactions.models import Appointment
from apps.social.models import Reaction

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO WISHLIST VIEWSET
# ==============================================================================

wishlist_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Lấy danh sách yêu thích của người dùng",
        description="Trả về danh sách các tin đăng mà người dùng hiện tại đã thêm vào mục yêu thích."
    ),
    create=extend_schema(
        summary="Thêm tin đăng vào danh sách yêu thích",
        description="Thêm một tin đăng vào danh sách yêu thích của người dùng hiện tại bằng `listing_id`."
    ),
    retrieve=extend_schema(summary="Lấy chi tiết một mục yêu thích"),
    destroy=extend_schema(summary="Xóa tin đăng khỏi danh sách yêu thích"),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO APPOINTMENT VIEWSET
# ==============================================================================

appointment_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Lấy danh sách lịch hẹn",
        description=(
            "Quản trị viên có thể xem tất cả lịch hẹn. "
            "Người dùng thông thường chỉ có thể xem các lịch hẹn họ đã tạo hoặc các lịch hẹn liên quan đến tin đăng của họ."
        )
    ),
    retrieve=extend_schema(summary="Lấy chi tiết một lịch hẹn"),
    create=extend_schema(
        summary="Tạo một lịch hẹn xem BĐS",
        description="Tạo một lịch hẹn mới cho một tin đăng. Yêu cầu người dùng phải xác thực danh tính (eKYC).",
        examples=[
            OpenApiExample(
                'Ví dụ tạo lịch hẹn',
                value={
                    "listing_id": 123,
                    "appointment_date": "2025-12-25T10:00:00Z",
                    "note": "Tôi muốn xem nhà vào buổi sáng."
                }
            )
        ]
    ),
    # Các action PUT, PATCH, DELETE mặc định không được sử dụng trực tiếp trong view của bạn
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)

# Schema cho action tùy chỉnh `update_status`
update_appointment_status_schema = extend_schema(
    summary="Cập nhật trạng thái lịch hẹn",
    description=(
        "Cập nhật trạng thái của một lịch hẹn. Logic quyền:\n"
        "- **Chủ tin đăng hoặc Admin:** có thể chuyển trạng thái sang `CONFIRMED` hoặc `COMPLETED`.\n"
        "- **Người tạo lịch hẹn, chủ tin đăng, hoặc Admin:** có thể chuyển trạng thái sang `CANCELLED`."
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'enum': [choice[0] for choice in Appointment.Status.choices]
                }
            }
        }
    },
    responses={
        200: AppointmentSerializer,
        400: {'description': "Trường 'status' là bắt buộc."},
        403: {'description': 'Không có quyền thực hiện hành động này hoặc trạng thái không hợp lệ.'}
    }
)

review_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Lấy danh sách đánh giá của một BĐS",
        description="Trả về danh sách các đánh giá cho một bất động sản cụ thể, được truyền qua URL.",
        parameters=[
            OpenApiParameter('property_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của Bất động sản cha')
        ]
    ),
    create=extend_schema(
        summary="Gửi một đánh giá mới cho BĐS",
        description="Cho phép người dùng đã xác thực danh tính (eKYC) gửi đánh giá (rating và comment) cho một bất động sản.",
        request=ReviewSerializer,
        responses={201: ReviewSerializer}
    ),
    retrieve=extend_schema(summary="Lấy chi tiết một đánh giá"),
    update=extend_schema(summary="[Chủ sở hữu/Admin] Cập nhật một đánh giá"),
    partial_update=extend_schema(summary="[Chủ sở hữu/Admin] Cập nhật một phần đánh giá"),
    destroy=extend_schema(summary="[Chủ sở hữu/Admin] Xóa một đánh giá"),
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO POST VIEWSET
# ==============================================================================

post_viewset_schema = extend_schema_view(
    list=extend_schema(summary="Lấy danh sách bài đăng"),
    retrieve=extend_schema(summary="Lấy chi tiết một bài đăng"),
    create=extend_schema(summary="Tạo một bài đăng mới"),
    update=extend_schema(summary="Cập nhật bài đăng"),
    partial_update=extend_schema(summary="Cập nhật một phần bài đăng"),
    destroy=extend_schema(summary="Xóa một bài đăng"),
)

# Schema cho action tùy chỉnh `react`
react_post_schema = extend_schema(
    summary="Bày tỏ cảm xúc cho bài đăng",
    description=(
        "Thêm, sửa đổi, hoặc xóa một cảm xúc cho bài đăng.\n"
        "- Nếu người dùng chưa bày tỏ cảm xúc -> Tạo mới.\n"
        "- Nếu người dùng bấm lại cảm xúc cũ -> Xóa.\n"
        "- Nếu người dùng bấm cảm xúc khác -> Cập nhật."
    ),
    request=ReactionSerializer,
    responses={
        201: {'description': 'Tạo cảm xúc thành công.'},
        200: {'description': 'Cập nhật cảm xúc thành công.'},
        204: {'description': 'Xóa cảm xúc thành công (Không có nội dung trả về).'}
    },
    examples=[
        OpenApiExample(
            'Ví dụ',
            value={'type': 'love'}
        )
    ]
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO COMMENT VIEWSET
# ==============================================================================

comment_viewset_schema = extend_schema_view(
    # Action: list (GET /api/posts/{post_pk}/comments/)
    list=extend_schema(
        summary="Lấy danh sách bình luận của bài đăng",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha')
        ]
    ),
    # Action: retrieve (GET /api/posts/{post_pk}/comments/{id}/)
    retrieve=extend_schema(
        summary="Lấy chi tiết một bình luận",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha'),
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bình luận')
        ]
    ),
    # Action: create (POST /api/posts/{post_pk}/comments/)
    create=extend_schema(
        summary="Tạo một bình luận mới",
        description="Đăng một bình luận mới cho bài đăng được chỉ định.",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha')
        ]
    ),
    # Action: update (PUT /api/posts/{post_pk}/comments/{id}/)
    update=extend_schema(
        summary="Cập nhật toàn bộ bình luận",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha'),
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bình luận')
        ]
    ),
    # Action: partial_update (PATCH /api/posts/{post_pk}/comments/{id}/)
    partial_update=extend_schema(
        summary="Cập nhật một phần bình luận",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha'),
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bình luận')
        ]
    ),
    # Action: destroy (DELETE /api/posts/{post_pk}/comments/{id}/)
    destroy=extend_schema(
        summary="Xóa một bình luận",
        parameters=[
            OpenApiParameter('post_pk', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bài đăng cha'),
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID của bình luận')
        ]
    ),
)