import pytest
from landifys.models import User, UserProfile
from landifys.serializers.accounts import UserCreateSerializer


@pytest.mark.django_db
class TestUserCreateSerializer:
    """
    Bộ test case cho UserCreateSerializer.
    """

    def test_serializer_with_valid_data(self):
        """
        KỊCH BẢN: Thành công
        Kiểm tra serializer hợp lệ với đầy đủ dữ liệu đúng.
        """
        valid_data = {
            "username": "testuser",
            "password": "strongpassword123",
            "phone_number": "0987654321",
            "first_name": "Test",
            "last_name": "User",
        }
        serializer = UserCreateSerializer(data=valid_data)

        assert serializer.is_valid(raise_exception=True) is True
        assert "password" not in serializer.data  # Kiểm tra password là write_only

    def test_serializer_missing_required_fields(self):
        """
        KỊCH BẢN: Thất bại - Thiếu trường bắt buộc
        Kiểm tra serializer báo lỗi khi thiếu các trường 'first_name', 'last_name'.
        """
        invalid_data = {
            "username": "testuser",
            "password": "strongpassword123",
        }
        serializer = UserCreateSerializer(data=invalid_data)

        assert serializer.is_valid() is False
        assert "first_name" in serializer.errors
        assert "last_name" in serializer.errors
        assert serializer.errors["first_name"][0].code == "required"
        assert serializer.errors["last_name"][0].code == "required"

    def test_serializer_with_duplicate_username(self, user_factory):
        """
        KỊCH BẢN: Thất bại - Trùng username
        Kiểm tra serializer báo lỗi khi username đã tồn tại.
        """
        # ARRANGE: Tạo một user đã tồn tại trong CSDL
        user_factory(username="existinguser")

        duplicate_data = {
            "username": "existinguser",
            "password": "password123",
            "first_name": "Another",
            "last_name": "User",
        }
        serializer = UserCreateSerializer(data=duplicate_data)

        assert serializer.is_valid() is False
        assert "username" in serializer.errors
        assert serializer.errors["username"][0].code == "unique"

    @pytest.mark.django_db
    def test_create_method_hashes_password(self):
        """
        KỊCH BẢN: Thành công - Logic tạo user
        Kiểm tra phương thức .create() của serializer:
        1. Tạo một đối tượng User.
        2. Hash mật khẩu một cách chính xác.
        """
        valid_data = {"username": "newuser", "password": "plaintextpassword", "first_name": "New", "last_name": "User"}
        serializer = UserCreateSerializer(data=valid_data)
        serializer.is_valid(raise_exception=True)

        # ACT: Gọi phương thức create
        user = serializer.save()

        # ASSERT
        assert isinstance(user, User)
        assert User.objects.count() == 1
        assert user.username == "newuser"
        assert user.password != "plaintextpassword"
        assert user.check_password("plaintextpassword") is True
