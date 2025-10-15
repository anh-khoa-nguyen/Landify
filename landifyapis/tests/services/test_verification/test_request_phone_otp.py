from unittest.mock import patch

import pytest
from landifys.models import User
from landifys.services import BusinessLogicError, verification


@pytest.mark.django_db
@pytest.mark.step_log
def test_request_otp_fails_if_user_has_no_phone(log_step):
    """KỊCH BẢN: Thất bại - Người dùng chưa có SĐT."""
    log_step("ARRANGE: Tạo người dùng không có số điện thoại.")
    user = User.objects.create_user(username="testuser", phone_number=None)

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(BusinessLogicError, match="Bạn chưa cập nhật số điện thoại."):
        verification.request_phone_otp(user=user)
    log_step("=> PASSED!")


# Mock đồng thời nhiều hàm trong các module utils
@patch("landifys.utils.sms.send_sms")
@patch("landifys.utils.otp.save_otp_to_cache")
@patch("landifys.utils.otp.generate_otp")
@pytest.mark.django_db
@pytest.mark.step_log
def test_request_otp_successfully(mock_generate_otp, mock_save_otp, mock_send_sms, log_step):
    """KỊCH BẢN: Thành công - Gửi OTP thành công."""
    log_step("ARRANGE: Cấu hình các hàm mock.")
    mock_generate_otp.return_value = "123456"
    mock_send_sms.return_value = {"message": "SMS sent successfully"}

    log_step("ARRANGE: Tạo người dùng có SĐT.")
    user = User.objects.create_user(username="testuser", phone_number="+84987654321")

    log_step("ACT: Gọi service request_phone_otp.")
    verification.request_phone_otp(user=user)

    log_step("ASSERT: Hàm generate_otp được gọi 1 lần.")
    mock_generate_otp.assert_called_once()

    log_step("ASSERT: Hàm save_otp_to_cache được gọi với đúng SĐT và mã OTP.")
    mock_save_otp.assert_called_once_with(user.phone_number, "123456")

    log_step("ASSERT: Hàm send_sms được gọi với đúng SĐT và nội dung tin nhắn.")
    mock_send_sms.assert_called_once()
    # Lấy các tham số đã được dùng để gọi hàm mock
    args, kwargs = mock_send_sms.call_args
    assert args[0] == user.phone_number
    assert "123456" in args[1]
    log_step("=> PASSED!")
