import pytest
from landifys.models import User, UserProfile
from landifys.serializers.accounts import UserCreateSerializer
from landifys.services import accounts


@pytest.mark.django_db
@pytest.mark.step_log
def test_create_user_successfully(log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra rằng hàm create_user:
    1. Tạo một đối tượng User trong CSDL.
    2. Mật khẩu được hash chính xác.
    3. Tự động tạo một đối tượng UserProfile liên kết.
    """
    log_step("ARRANGE: Chuẩn bị dữ liệu hợp lệ cho việc đăng ký.")
    user_data = {"username": "newuser", "password": "password123", "first_name": "New", "last_name": "User"}

    log_step("ARRANGE: Tạo một instance của serializer và validate dữ liệu.")
    serializer = UserCreateSerializer(data=user_data)
    assert serializer.is_valid(raise_exception=True) is True

    log_step("ACT: Gọi hàm service create_user.")
    created_user = accounts.create_user(serializer=serializer)

    log_step("ASSERT: Một User đã được tạo trong CSDL.")
    assert User.objects.count() == 1

    log_step("ASSERT: Thông tin người dùng được lưu chính xác.")
    assert created_user.username == "newuser"

    log_step("ASSERT: Mật khẩu đã được hash (không phải plain text).")
    assert created_user.check_password("password123") is True
    assert created_user.password != "password123"

    log_step("ASSERT: Một UserProfile đã được tạo và liên kết với User.")
    assert UserProfile.objects.count() == 1
    assert created_user.profile is not None
    assert UserProfile.objects.first().user == created_user
    log_step("=> PASSED!")
