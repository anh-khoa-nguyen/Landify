# tests/serializers/test_accounts/test_user_serializer.py
import pytest
from landifys.serializers.accounts import UserSerializer


@pytest.mark.django_db
class TestUserSerializer:
    """
    Bộ test case cho UserSerializer (chuyên về serialization).
    """

    def test_serialization_contains_expected_fields(self, user_factory):
        """
        KỊCH BẢN: Thành công
        Kiểm tra JSON đầu ra chứa đúng và đủ các trường đã định nghĩa.
        """
        user = user_factory(
            username="testuser", first_name="Test", last_name="User", email="test@example.com", role="admin"
        )
        serializer = UserSerializer(instance=user)
        data = serializer.data

        expected_keys = [
            "id",
            "username",
            "first_name",
            "last_name",
            "get_full_name",
            "email",
            "role",
            "phone_number",
            "is_phone_verified",
            "is_id_card_verified",
            "is_identity_verified",
            "date_joined",
        ]

        assert set(data.keys()) == set(expected_keys)

    def test_get_full_name_serialization(self, user_factory):
        """
        KỊCH BẢN: Thành công
        Kiểm tra trường 'get_full_name' được serialize chính xác.
        """
        user = user_factory(first_name="John", last_name="Doe")
        serializer = UserSerializer(instance=user)

        assert serializer.data["get_full_name"] == "John Doe"
