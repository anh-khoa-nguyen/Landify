# landifys/docs/social_docs.py

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view

from apps.social.models import Reaction

# Import serializers để mô tả request/response
from apps.social.serializers import CommentSerializer, PostSerializer, ReactionSerializer

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO POST VIEWSET
# ==============================================================================

post_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Lấy danh sách bài đăng",
        description="Trả về danh sách các bài đăng đang hoạt động, đã được sắp xếp và phân trang. Mỗi bài đăng bao gồm số lượng bình luận và cảm xúc.",
    ),
    retrieve=extend_schema(
        summary="Lấy chi tiết một bài đăng",
        description="Lấy thông tin chi tiết của một bài đăng, bao gồm cả cảm xúc của người dùng hiện tại trên bài đăng đó (nếu có).",
    ),
    create=extend_schema(summary="Tạo một bài đăng mới"),
    update=extend_schema(summary="Cập nhật toàn bộ bài đăng"),
    partial_update=extend_schema(summary="Cập nhật một phần bài đăng"),
    destroy=extend_schema(summary="Xóa một bài đăng"),
)

# Schema cho action tùy chỉnh `react`
react_post_schema = extend_schema(
    summary="Bày tỏ cảm xúc cho bài đăng",
    description=(
        "Thêm, sửa đổi, hoặc xóa một cảm xúc cho bài đăng.\n"
        "- Nếu người dùng chưa bày tỏ cảm xúc -> Tạo mới (Trả về 201).\n"
        "- Nếu người dùng bấm lại cảm xúc cũ -> Xóa (Trả về 204).\n"
        "- Nếu người dùng bấm cảm xúc khác -> Cập nhật (Trả về 200)."
    ),
    request=ReactionSerializer,
    responses={
        201: ReactionSerializer,
        200: ReactionSerializer,
        204: {"description": "Xóa cảm xúc thành công (Không có nội dung trả về)."},
    },
    examples=[OpenApiExample("Ví dụ", summary='Bày tỏ cảm xúc "Yêu thích"', value={"type": "love"})],
)

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO COMMENT VIEWSET
# ==============================================================================

comment_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Lấy danh sách bình luận của bài đăng",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha")
        ],
    ),
    retrieve=extend_schema(
        summary="Lấy chi tiết một bình luận",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha"),
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bình luận"),
        ],
    ),
    create=extend_schema(
        summary="Tạo một bình luận mới",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha")
        ],
    ),
    update=extend_schema(
        summary="Cập nhật toàn bộ bình luận",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha"),
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bình luận"),
        ],
    ),
    partial_update=extend_schema(
        summary="Cập nhật một phần bình luận",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha"),
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bình luận"),
        ],
    ),
    destroy=extend_schema(
        summary="Xóa một bình luận",
        parameters=[
            OpenApiParameter("post_pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bài đăng cha"),
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID của bình luận"),
        ],
    ),
)
