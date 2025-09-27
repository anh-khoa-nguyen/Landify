import pytest
from landifys.services import accounts, BusinessLogicError
from landifys.models import User

@pytest.mark.django_db
@pytest.mark.step_log
def test_change_password_with_incorrect_old_password(log_step):
    """
    KỊCH BẢN: Thất bại
    Kiểm tra rằng hệ thống ném ra lỗi khi người dùng cung cấp sai mật khẩu cũ.
    """
    log_step("ARRANGE: Tạo một người dùng với mật khẩu 'old_password'.")
    user = User.objects.create_user(username='testuser', password='old_password')

    log_step("ACT & ASSERT: Gọi service với mật khẩu cũ sai và kiểm tra exception.")
    with pytest.raises(BusinessLogicError, match="Mật khẩu cũ không chính xác."):
        accounts.change_user_password(
            user=user,
            old_password='wrong_old_password',
            new_password='new_password'
        )
    log_step("=> PASSED!")

@pytest.mark.django_db
@pytest.mark.step_log
def test_change_password_successfully(log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra rằng mật khẩu được thay đổi thành công và có thể dùng để xác thực.
    """
    log_step("ARRANGE: Tạo một người dùng với mật khẩu 'old_password'.")
    user = User.objects.create_user(username='testuser', password='old_password')

    log_step("ACT: Gọi service với mật khẩu cũ chính xác.")
    accounts.change_user_password(
        user=user,
        old_password='old_password',
        new_password='new_password_123'
    )

    log_step("ASSERT: Người dùng không thể đăng nhập bằng mật khẩu cũ nữa.")
    # refresh_from_db để đảm bảo chúng ta có object user mới nhất từ CSDL
    user.refresh_from_db()
    assert user.check_password('old_password') is False

    log_step("ASSERT: Người dùng có thể đăng nhập bằng mật khẩu mới.")
    assert user.check_password('new_password_123') is True
    log_step("=> PASSED!")