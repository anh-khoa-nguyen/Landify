# tests/serializers/test_accounts/test_user_update_serializer.py
import pytest
from landifys.serializers.accounts import UserUpdateSerializer

@pytest.mark.django_db
class TestUserUpdateSerializer:
    """
    Bộ test case cho UserUpdateSerializer.
    """

    def test_serializer_updates_allowed_fields(self, user_factory):
        """
        KỊCH BẢN: Thành công
        Kiểm tra serializer cập nhật thành công các trường cho phép (first_name, last_name, email).
        """
        user = user_factory(first_name="Old", last_name="Name", email="old@example.com")
        update_data = {
            "first_name": "New",
            "last_name": "Name",
            "email": "new@example.com"
        }
        serializer = UserUpdateSerializer(instance=user, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()

        assert updated_user.first_name == "New"
        assert updated_user.last_name == "Name"
        assert updated_user.email == "new@example.com"

    def test_serializer_ignores_disallowed_fields(self, user_factory):
        """
        KỊCH BẢN: Thành công - Bỏ qua trường không cho phép
        Kiểm tra serializer bỏ qua các trường không được phép cập nhật như 'username' hay 'role'.
        """
        user = user_factory(username="original_user", role="user")
        malicious_data = {
            "username": "hacked_user",
            "role": "admin",
            "first_name": "Updated"
        }
        serializer = UserUpdateSerializer(instance=user, data=malicious_data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()

        # ASSERT: Các trường không được phép không bị thay đổi
        assert updated_user.username == "original_user"
        assert updated_user.role == "user"
        # ASSERT: Trường được phép vẫn được cập nhật
        assert updated_user.first_name == "Updated"