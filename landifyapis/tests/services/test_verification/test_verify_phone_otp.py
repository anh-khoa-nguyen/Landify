from unittest.mock import patch

import pytest
from landifys.models import User
from landifys.services import verification


@patch("landifys.utils.otp.verify_otp_from_cache")
@pytest.mark.django_db
@pytest.mark.step_log
def test_verify_otp_fails_with_incorrect_code(mock_verify_from_cache, log_step):
    """KỊCH BẢN: Thất bại - Mã OTP không chính xác."""
    log_step("ARRANGE: Cấu hình mock trả về False (xác thực thất bại).")
    mock_verify_from_cache.return_value = False

    log_step("ARRANGE: Tạo người dùng chưa xác thực SĐT.")
    user = User.objects.create_user(username="testuser", phone_number="+84123456789", is_phone_verified=False)

    log_step("ACT: Gọi service với một mã OTP bất kỳ.")
    is_verified = verification.verify_phone_otp(user=user, otp_code="wrong_code")

    log_step("ASSERT: Hàm verify_otp_from_cache được gọi.")
    mock_verify_from_cache.assert_called_once_with(user.phone_number, "wrong_code")

    log_step("ASSERT: Kết quả trả về là False.")
    assert is_verified is False

    user.refresh_from_db()
    log_step("ASSERT: Trạng thái is_phone_verified của người dùng không thay đổi.")
    assert user.is_phone_verified is False
    log_step("=> PASSED!")


@patch("landifys.utils.otp.verify_otp_from_cache")
@pytest.mark.django_db
@pytest.mark.step_log
def test_verify_otp_succeeds_with_correct_code(mock_verify_from_cache, log_step):
    """KỊCH BẢN: Thành công - Mã OTP chính xác."""
    log_step("ARRANGE: Cấu hình mock trả về True (xác thực thành công).")
    mock_verify_from_cache.return_value = True

    log_step("ARRANGE: Tạo người dùng chưa xác thực SĐT.")
    user = User.objects.create_user(username="testuser", phone_number="+84123456789", is_phone_verified=False)

    log_step("ACT: Gọi service với một mã OTP.")
    is_verified = verification.verify_phone_otp(user=user, otp_code="correct_code")

    log_step("ASSERT: Kết quả trả về là True.")
    assert is_verified is True

    user.refresh_from_db()
    log_step("ASSERT: Trạng thái is_phone_verified của người dùng được cập nhật thành True.")
    assert user.is_phone_verified is True
    log_step("=> PASSED!")
