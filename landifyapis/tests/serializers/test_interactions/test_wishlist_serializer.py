# tests/serializers/test_interactions/test_wishlist_serializer.py
import pytest
from landifys.serializers.interactions import WishlistSerializer


@pytest.mark.django_db
class TestWishlistSerializer:
    """
    Bộ test case cho WishlistSerializer.
    """

    def test_serialization_contains_nested_listing(self, user_factory, listing_factory, wishlist_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng cấu trúc JSON với dữ liệu listing lồng nhau.
        """
        # ARRANGE
        user = user_factory()
        listing = listing_factory(title="Dream House")
        wishlist_item = wishlist_factory(user=user, listing=listing)

        # ACT
        serializer = WishlistSerializer(instance=wishlist_item)
        data = serializer.data

        # ASSERT
        expected_keys = {"id", "user", "listing"}
        assert set(data.keys()) == expected_keys
        assert data["listing"]["title"] == "Dream House"
        # Kiểm tra trường write_only không xuất hiện trong output
        assert "listing_id" not in data

    def test_deserialization_with_valid_listing_id(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận `listing_id` hợp lệ.
        """
        # ARRANGE
        listing = listing_factory()
        valid_data = {"listing_id": listing.id}

        # ACT
        serializer = WishlistSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
        assert serializer.validated_data['listing'] == listing

    def test_deserialization_with_non_existent_listing_id(self):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi `listing_id` không tồn tại.
        """
        # ARRANGE
        invalid_data = {"listing_id": 99999}  # ID không tồn tại

        # ACT
        serializer = WishlistSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "listing_id" in serializer.errors
        assert serializer.errors["listing_id"][0].code == "does_not_exist"