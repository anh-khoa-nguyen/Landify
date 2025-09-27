# tests/serializers/test_moderation/test_protest_serializer.py
import pytest
from landifys.serializers.moderation import ProtestSerializer

@pytest.mark.django_db
class TestProtestSerializer:
    """
    Bộ test case cho ProtestSerializer.
    """

    def test_serialization_contains_expected_data(self, user_factory, listing_factory, protest_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng cấu trúc JSON với dữ liệu lồng nhau.
        """
        # ARRANGE
        protester = user_factory(username="protester_user")
        admin = user_factory(username="admin_user", role="admin")
        listing = listing_factory(title="Tin đăng bị gỡ")
        protest = protest_factory(
            protester=protester,
            listing=listing,
            admin=admin,
            status="RESOLVED",
            resolution_note="Đã xem xét và duyệt lại."
        )

        # ACT
        serializer = ProtestSerializer(instance=protest)
        data = serializer.data

        # ASSERT
        expected_keys = {
            "id", "listing_title", "protester", "reason", "admin",
            "resolution_note", "status", "created_date", "updated_date"
        }
        # Lưu ý: 'listing' là write_only nên không có trong output
        assert set(data.keys()) == expected_keys
        assert data['listing_title'] == "Tin đăng bị gỡ"
        assert data['protester']['username'] == "protester_user"
        assert data['admin']['username'] == "admin_user"

    def test_deserialization_with_valid_data(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ để tạo mới.
        """
        # ARRANGE
        listing = listing_factory()
        valid_data = {
            "listing": listing.id,
            "reason": "Tôi tin rằng tin đăng của tôi không vi phạm."
        }

        # ACT
        serializer = ProtestSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
        assert serializer.validated_data['listing'] == listing

    def test_deserialization_fails_without_required_fields(self):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi thiếu các trường bắt buộc.
        """
        # ARRANGE
        invalid_data = {} # Thiếu cả 'listing' và 'reason'

        # ACT
        serializer = ProtestSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "listing" in serializer.errors
        assert "reason" in serializer.errors