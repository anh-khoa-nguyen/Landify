# tests/serializers/test_social/test_post_serializer.py
import pytest
from django.contrib.auth.models import AnonymousUser
from landifys.models import Reaction
from landifys.serializers.social import PostSerializer
from rest_framework.test import APIRequestFactory


@pytest.mark.django_db
class TestPostSerializer:
    """
    Bộ test case cho PostSerializer.
    """

    @pytest.fixture
    def mock_request(self):
        """Tạo một request giả để đưa vào context của serializer."""
        factory = APIRequestFactory()
        return factory.get("/")

    def test_serialization_contains_annotated_fields(self, user_factory, post_factory, mock_request):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng các trường, bao gồm cả các trường
        được tính toán (annotated) từ view.
        """
        # ARRANGE
        user = user_factory()
        post = post_factory(user=user)
        # Gán các giá trị annotated giả lập
        post.comment_count = 5
        post.reaction_count = 10

        # ACT
        # Truyền request vào context để SerializerMethodField hoạt động
        serializer = PostSerializer(instance=post, context={"request": mock_request})
        data = serializer.data

        # ASSERT
        expected_keys = {
            "id",
            "user",
            "title",
            "content",
            "created_date",
            "updated_date",
            "comment_count",
            "reaction_count",
            "current_user_reaction",
        }
        assert set(data.keys()) == set(expected_keys)
        assert data["comment_count"] == 5
        assert data["reaction_count"] == 10

    def test_current_user_reaction_is_null_for_unauthenticated_user(self, post_factory, mock_request):
        """
        KỊCH BẢN: Thành công - Không có reaction
        Kiểm tra 'current_user_reaction' là null khi người dùng chưa đăng nhập.
        """
        # ARRANGE
        post = post_factory()
        # Giả lập request từ người dùng ẩn danh
        mock_request.user = AnonymousUser()

        # ACT
        serializer = PostSerializer(instance=post, context={"request": mock_request})

        # ASSERT
        assert serializer.data["current_user_reaction"] is None

    def test_current_user_reaction_is_null_when_user_has_not_reacted(self, user_factory, post_factory, mock_request):
        """
        KỊCH BẢN: Thành công - Không có reaction
        Kiểm tra 'current_user_reaction' là null khi người dùng đã đăng nhập nhưng chưa react.
        """
        # ARRANGE
        post = post_factory()
        current_user = user_factory()
        mock_request.user = current_user

        # ACT
        serializer = PostSerializer(instance=post, context={"request": mock_request})

        # ASSERT
        assert serializer.data["current_user_reaction"] is None

    def test_current_user_reaction_returns_correct_type(
        self, user_factory, post_factory, reaction_factory, mock_request
    ):
        """
        KỊCH BẢN: Thành công - Có reaction
        Kiểm tra 'current_user_reaction' trả về đúng loại cảm xúc mà người dùng đã bày tỏ.
        """
        # ARRANGE
        post = post_factory()
        current_user = user_factory()
        other_user = user_factory()
        mock_request.user = current_user

        # Người dùng khác react 'like'
        reaction_factory(user=other_user, post=post, type=Reaction.Type.LIKE)
        # Người dùng hiện tại react 'love'
        reaction_factory(user=current_user, post=post, type=Reaction.Type.LOVE)

        # ACT
        serializer = PostSerializer(instance=post, context={"request": mock_request})

        # ASSERT
        assert serializer.data["current_user_reaction"] == Reaction.Type.LOVE
