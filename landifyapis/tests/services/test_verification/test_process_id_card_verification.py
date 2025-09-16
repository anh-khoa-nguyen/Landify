import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from landifys.services import verification, EkycError
from landifys.models import User


@patch('landifys.utils.ekyc.call_fpt_idr_api')
@pytest.mark.django_db
@pytest.mark.step_log
def test_process_id_card_fails_on_api_error(mock_fpt_api, log_step):
    """KỊCH BẢN: Thất bại - API FPT trả về lỗi."""
    log_step("ARRANGE: Cấu hình mock API FPT trả về errorCode khác 0.")
    mock_fpt_api.return_value = {"errorCode": 1, "errorMessage": "Ảnh không hợp lệ"}

    log_step("ARRANGE: Tạo người dùng và file ảnh giả.")
    user = User.objects.create_user(username='testuser')
    fake_image = SimpleUploadedFile("id.jpg", b"content", content_type="image/jpeg")

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(EkycError, match="Không thể đọc thông tin từ ảnh CCCD."):
        verification.process_id_card_verification(user=user, id_card_image=fake_image)
    log_step("=> PASSED!")


@patch('django.core.cache.cache.set')
# @patch('landifys.utils.ekyc.call_fpt_idr_api')
@pytest.mark.django_db
@pytest.mark.step_log
def test_process_id_card_succeeds(mock_fpt_api, mock_cache_set, log_step):
    """KỊCH BẢN: Thành công - Xử lý ảnh CCCD thành công."""
    log_step("ARRANGE: Cấu hình mock API FPT trả về dữ liệu thành công.")
    extracted_data = {"id": "0123456789", "name": "NGUYEN VAN A"}
    mock_fpt_api.return_value = {"errorCode": 0, "data": [extracted_data]}

    log_step("ARRANGE: Tạo người dùng và file ảnh giả.")
    user = User.objects.create_user(username='testuser', is_id_card_verified=False)
    fake_image_content = b"image_content_bytes"
    fake_image = SimpleUploadedFile("id.jpg", fake_image_content, content_type="image/jpeg")

    log_step("ACT: Gọi service.")
    result = verification.process_id_card_verification(user=user, id_card_image=fake_image)

    log_step("ASSERT: Dữ liệu trả về từ service là chính xác.")
    assert result == extracted_data

    log_step("ASSERT: Dữ liệu ảnh được lưu vào cache.")
    mock_cache_set.assert_called_once_with(f"ekyc_image_{user.id}", fake_image_content, timeout=600)

    user.refresh_from_db()
    log_step("ASSERT: Trạng thái is_id_card_verified của người dùng được cập nhật.")
    assert user.is_id_card_verified is True
    log_step("=> PASSED!")