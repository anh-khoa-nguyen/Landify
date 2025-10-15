from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from landifys.models import User
from landifys.services import EkycError, verification


@pytest.mark.django_db
@pytest.mark.step_log
def test_liveness_check_fails_if_no_cached_image(log_step):
    """KỊCH BẢN: Thất bại - Phiên làm việc hết hạn (không có ảnh trong cache)."""
    log_step("ARRANGE: Tạo người dùng và file video giả. Đảm bảo cache trống.")
    user = User.objects.create_user(username="testuser")
    fake_video = SimpleUploadedFile("video.mp4", b"content", content_type="video/mp4")
    cache.clear()

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(EkycError, match="Phiên xác thực đã hết hạn"):
        verification.complete_ekyc_liveness_check(user=user, video_file=fake_video)
    log_step("=> PASSED!")


@patch("landifys.utils.ekyc.call_fpt_liveness_api")
@pytest.mark.django_db
@pytest.mark.step_log
def test_liveness_check_fails_if_not_live_or_not_match(mock_fpt_api, log_step):
    """KỊCH BẢN: Thất bại - API FPT trả về kết quả không hợp lệ."""
    log_step("ARRANGE: Tạo người dùng, video và lưu ảnh vào cache.")
    user = User.objects.create_user(username="testuser")
    fake_video = SimpleUploadedFile("video.mp4", b"content", content_type="video/mp4")
    cache.set(f"ekyc_image_{user.id}", b"image_data")

    log_step("--- Trường hợp 1: Không phải người thật ---")
    mock_fpt_api.return_value = {"liveness": {"is_live": "false"}, "face_match": {"isMatch": "true"}}
    with pytest.raises(EkycError, match="Hệ thống nhận diện không phải người thật."):
        verification.complete_ekyc_liveness_check(user=user, video_file=fake_video)

    log_step("--- Trường hợp 2: Khuôn mặt không khớp ---")
    mock_fpt_api.return_value = {"liveness": {"is_live": "true"}, "face_match": {"isMatch": "false"}}
    with pytest.raises(EkycError, match="Khuôn mặt không khớp với ảnh trên CCCD."):
        verification.complete_ekyc_liveness_check(user=user, video_file=fake_video)
    log_step("=> PASSED!")


@patch("django.core.cache.cache.delete")
@patch("landifys.utils.ekyc.call_fpt_liveness_api")
@pytest.mark.django_db
@pytest.mark.step_log
def test_liveness_check_succeeds(mock_fpt_api, mock_cache_delete, log_step):
    """KỊCH BẢN: Thành công - Hoàn tất eKYC."""
    log_step("ARRANGE: Cấu hình mock API FPT trả về kết quả thành công.")
    mock_fpt_api.return_value = {"liveness": {"is_live": "true"}, "face_match": {"isMatch": "true"}}

    log_step("ARRANGE: Tạo người dùng, video và lưu ảnh vào cache.")
    user = User.objects.create_user(username="testuser", is_identity_verified=False)
    fake_video = SimpleUploadedFile("video.mp4", b"content", content_type="video/mp4")
    cache.set(f"ekyc_image_{user.id}", b"image_data")

    log_step("ACT: Gọi service.")
    verification.complete_ekyc_liveness_check(user=user, video_file=fake_video)

    log_step("ASSERT: Trạng thái is_identity_verified của người dùng được cập nhật.")
    user.refresh_from_db()
    assert user.is_identity_verified is True

    log_step("ASSERT: Dữ liệu ảnh trong cache đã được xóa.")
    mock_cache_delete.assert_called_once_with(f"ekyc_image_{user.id}")
    log_step("=> PASSED!")
