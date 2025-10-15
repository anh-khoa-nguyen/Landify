# tests/serializers/test_social/test_reaction_serializer.py
import pytest
from landifys.models import Reaction
from landifys.serializers.social import ReactionSerializer


class TestReactionSerializer:
    """
    Bộ test case cho ReactionSerializer.
    """

    @pytest.mark.parametrize("reaction_type", ["like", "love", "haha", "wow", "sad", "angry"])
    def test_serializer_with_valid_reaction_type(self, reaction_type):
        """
        KỊCH BẢN: Thành công
        Kiểm tra serializer hợp lệ với các loại reaction được cho phép.
        """
        data = {"type": reaction_type}
        serializer = ReactionSerializer(data=data)
        assert serializer.is_valid(raise_exception=True) is True

    def test_serializer_with_invalid_reaction_type(self):
        """
        KỊCH BẢN: Thất bại
        Kiểm tra serializer báo lỗi khi 'type' không nằm trong danh sách choices.
        """
        data = {"type": "invalid_reaction"}
        serializer = ReactionSerializer(data=data)
        assert serializer.is_valid() is False
        assert "type" in serializer.errors

    def test_serializer_with_missing_type(self):
        """
        KỊCH BẢN: Thất bại
        Kiểm tra serializer báo lỗi khi thiếu trường 'type'.
        """
        data = {}
        serializer = ReactionSerializer(data=data)
        assert serializer.is_valid() is False
        assert "type" in serializer.errors
        assert serializer.errors["type"][0].code == "required"
