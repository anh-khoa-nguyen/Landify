from unittest.mock import patch

import pytest

# Import RtcTokenBuilder để có thể tham chiếu đến Role_Publisher
from agora_token_builder import RtcTokenBuilder
from django.test import override_settings
from landifys.models import User
from landifys.services import BusinessLogicError, integrations


@pytest.fixture
def test_user():
    """Một fixture đơn giản để tạo người dùng cho các test case."""
    return User.objects.create_user(username="testuser", id=123)


@pytest.mark.django_db
@pytest.mark.step_log
def test_generate_token_fails_without_channel_name(log_step, test_user):
    """
    KỊCH BẢN 1: Thất bại - Thiếu channelName.
    """
    log_step("ARRANGE: Chuẩn bị đầu vào với channel_name là chuỗi rỗng.")

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(BusinessLogicError, match="channelName là bắt buộc."):
        integrations.generate_agora_token(channel_name="", uid=test_user.id)
    log_step("=> PASSED!")


# Kỹ thuật quan trọng:
# 1. @override_settings: Đảm bảo test dùng các giá trị settings giả lập,
#    không phụ thuộc vào file .env thật.
# 2. @patch('time.time'): "Đóng băng" thời gian để có thể tính toán chính xác
#    thời gian hết hạn của token.
# 3. @patch('RtcTokenBuilder.buildTokenWithUid'): Giả lập hàm của thư viện Agora,
#    tránh việc gọi ra ngoài và giúp ta kiểm tra các tham số đầu vào.
@override_settings(AGORA_APP_ID="test_app_id", AGORA_APP_CERTIFICATE="test_app_cert")
@patch("landifys.services.integrations.time.time")
@patch("landifys.services.integrations.RtcTokenBuilder.buildTokenWithUid")
@pytest.mark.django_db
@pytest.mark.step_log
def test_generate_token_successfully(mock_rtc_builder, mock_time, log_step, test_user):
    """
    KỊCH BẢN 2: Thành công - Tạo token thành công với các tham số chính xác.
    """
    log_step("ARRANGE: Cấu hình các giá trị trả về giả lập.")
    fixed_timestamp = 1700000000  # Một mốc thời gian cố định
    mock_time.return_value = fixed_timestamp
    mock_rtc_builder.return_value = "fake_generated_agora_token"

    log_step("ACT: Gọi service với các tham số hợp lệ.")
    result = integrations.generate_agora_token(channel_name="test-channel", uid=test_user.id)

    log_step("ASSERT: Kiểm tra kết quả trả về từ service.")
    assert result == {"token": "fake_generated_agora_token", "uid": test_user.id}

    log_step("ASSERT: Kiểm tra xem hàm của thư viện Agora có được gọi với ĐÚNG các tham số không.")
    # Tính toán chính xác thời gian hết hạn mà hàm thật sẽ tính
    expected_expiry_ts = fixed_timestamp + 3600

    ROLE_PUBLISHER = 1  # Vai trò của người phát sóng (broadcaster)

    # Đây là bước kiểm tra chi tiết nhất, "không ẩu"
    mock_rtc_builder.assert_called_once_with(
        "test_app_id",  # app_id từ override_settings
        "test_app_cert",  # app_certificate từ override_settings
        "test-channel",  # channel_name từ input
        test_user.id,  # uid từ input
        ROLE_PUBLISHER,  # vai trò (role) được hardcode
        expected_expiry_ts,  # thời gian hết hạn được tính toán chính xác
    )
    log_step("=> PASSED!")


@override_settings(AGORA_APP_ID="test_app_id", AGORA_APP_CERTIFICATE="test_app_cert")
@patch("landifys.services.integrations.RtcTokenBuilder.buildTokenWithUid")
@pytest.mark.django_db
@pytest.mark.step_log
def test_generate_token_handles_builder_exception(mock_rtc_builder, log_step, test_user):
    """
    KỊCH BẢN 3: Thất bại - Thư viện Agora ném ra lỗi.
    """
    log_step("ARRANGE: Cấu hình mock để ném ra một exception.")
    mock_rtc_builder.side_effect = Exception("Lỗi từ thư viện Agora")

    log_step("ACT & ASSERT: Gọi service và kiểm tra xem nó có bắt và gói lỗi lại không.")
    with pytest.raises(BusinessLogicError) as excinfo:
        integrations.generate_agora_token(channel_name="test-channel", uid=test_user.id)

    log_step("ASSERT: Kiểm tra nội dung của thông điệp lỗi được gói lại.")
    assert "Lỗi tạo token Agora: Lỗi từ thư viện Agora" in str(excinfo.value)
    log_step("=> PASSED!")
