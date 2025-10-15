# tests/serializers/test_interactions/test_review_serializer.py
import pytest
from landifys.serializers.interactions import ReviewSerializer


@pytest.mark.django_db
class TestReviewSerializer:
    """
    Bộ test case cho ReviewSerializer.
    """

    def test_serialization_contains_expected_data(self, user_factory, property_factory, review_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng cấu trúc JSON với dữ liệu user lồng nhau.
        """
        # ARRANGE
        user = user_factory(first_name="John", last_name="Doe")
        prop = property_factory()
        review = review_factory(user=user, property=prop, rating=5, comment="Excellent!")

        # ACT
        serializer = ReviewSerializer(instance=review)
        data = serializer.data

        # ASSERT
        expected_keys = {"id", "user", "property", "rating", "comment", "active", "created_date", "updated_date"}
        assert set(data.keys()) == expected_keys
        assert data["rating"] == 5
        assert data["comment"] == "Excellent!"
        assert data["user"]["get_full_name"] == "John Doe"
        # Kiểm tra các trường chỉ đọc không thể được ghi vào
        assert "user" in ReviewSerializer.Meta.read_only_fields
        assert "property" in ReviewSerializer.Meta.read_only_fields

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ để tạo mới.
        """
        # ARRANGE
        valid_data = {"rating": 4, "comment": "Good place."}

        # ACT
        serializer = ReviewSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True

    @pytest.mark.parametrize("invalid_rating", [0, 6, "five", None])
    def test_deserialization_with_invalid_rating(self, invalid_rating):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi 'rating' không hợp lệ (ngoài khoảng 1-5, không phải số).
        """
        # ARRANGE
        invalid_data = {"rating": invalid_rating, "comment": "Invalid rating test."}

        # ACT
        serializer = ReviewSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "rating" in serializer.errors
