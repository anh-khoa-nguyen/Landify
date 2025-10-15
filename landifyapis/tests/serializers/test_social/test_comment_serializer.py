# tests/serializers/test_social/test_comment_serializer.py
import pytest
from landifys.serializers.social import CommentSerializer


@pytest.mark.django_db
class TestCommentSerializer:
    """
    Bộ test case cho CommentSerializer.
    """

    def test_serialization_contains_expected_data(self, user_factory, post_factory, comment_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng cấu trúc JSON với user lồng nhau.
        """
        # ARRANGE
        user = user_factory(first_name="Commenter")
        post = post_factory()
        comment = comment_factory(user=user, post=post, content="This is a test comment.")

        # ACT
        serializer = CommentSerializer(instance=comment)
        data = serializer.data

        # ASSERT
        expected_keys = {"id", "user", "post", "content", "active", "created_date", "updated_date"}
        assert set(data.keys()) == expected_keys
        assert data["content"] == "This is a test comment."
        assert data["user"]["get_full_name"] == user.get_full_name()
        assert "user" in CommentSerializer.Meta.read_only_fields
        assert "post" in CommentSerializer.Meta.read_only_fields

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ.
        """
        # ARRANGE
        valid_data = {"content": "A new valid comment."}

        # ACT
        serializer = CommentSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
