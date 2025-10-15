from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from landifys.models import Property, PropertyMedia, User
from landifys.services import listings


@patch("cloudinary.uploader.upload")
@pytest.mark.django_db
@pytest.mark.step_log
def test_add_media_to_property(mock_cloudinary_upload, log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra việc upload media và tạo bản ghi trong CSDL.
    """
    log_step("ARRANGE: Cấu hình mock Cloudinary.")
    mock_cloudinary_upload.return_value = {"secure_url": "http://fake.url/image.jpg", "public_id": "fake_public_id"}

    log_step("ARRANGE: Tạo user, property và file giả.")
    user = User.objects.create_user(username="testuser")
    prop = Property.objects.create(owner=user, area=1)
    fake_file = SimpleUploadedFile("test.jpg", b"content", "image/jpeg")

    log_step("ACT: Gọi service add_media_to_property.")
    media_object = listings.add_media_to_property(prop=prop, media_file=fake_file)

    log_step("ASSERT: Một đối tượng PropertyMedia đã được tạo.")
    assert PropertyMedia.objects.count() == 1

    log_step("ASSERT: Thông tin media được lưu chính xác.")
    assert media_object.property == prop
    assert media_object.url == "http://fake.url/image.jpg"
    assert media_object.public_id == "fake_public_id"
    log_step("=> PASSED!")
