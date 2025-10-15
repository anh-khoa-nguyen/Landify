# import pytest
# from unittest.mock import patch
# from django.core.files.uploadedfile import SimpleUploadedFile
# from landifys.services import accounts
# from landifys.models import User
#
#
# @patch('cloudinary.uploader.upload')
# @pytest.mark.django_db
# @pytest.mark.step_log
# def test_change_avatar_successfully(mock_cloudinary_upload, log_step):
#     """
#     KỊCH BẢN: Thành công
#     Kiểm tra việc thay đổi avatar có gọi đúng dịch vụ Cloudinary,
#     trả về đúng URL và lưu đúng các thành phần vào CSDL.
#     """
#     log_step("ARRANGE: Cấu hình response giả lập chi tiết từ Cloudinary.")
#     # Các thành phần cốt lõi của một file trên Cloudinary
#     fake_public_id = "avatars/1/sample"
#     fake_version = 1234567890
#     fake_format = "jpg"
#
#     # URL đầy đủ được tạo ra từ các thành phần trên
#     fake_secure_url = f"https://res.cloudinary.com/fake-cloud-name/image/upload/v{fake_version}/{fake_public_id}.{fake_format}"
#
#     mock_cloudinary_upload.return_value = {
#         "public_id": fake_public_id,
#         "version": fake_version,
#         "format": fake_format,
#         "secure_url": fake_secure_url
#     }
#
#     log_step("ARRANGE: Tạo một người dùng và một file ảnh giả.")
#     user = User.objects.create_user(username='testuser')
#     fake_avatar_file = SimpleUploadedFile(f"avatar.{fake_format}", b"file_content", content_type=f"image/{fake_format}")
#
#     log_step("ACT: Gọi hàm service change_user_avatar.")
#     returned_url = accounts.change_user_avatar(user=user, avatar_file=fake_avatar_file)
#
#     log_step("ASSERT: Hàm upload của Cloudinary được gọi đúng 1 lần.")
#     mock_cloudinary_upload.assert_called_once()
#
#     log_step("ASSERT: Service trả về đúng URL đầy đủ cho client.")
#     assert returned_url == fake_secure_url
#
#     log_step("ASSERT: Các thành phần của avatar trong UserProfile đã được lưu chính xác.")
#     user.refresh_from_db()
#
#     # Lấy đối tượng CloudinaryResource từ profile
#     avatar_resource = user.profile.avatar
#
#     # Kiểm tra các thuộc tính cốt lõi của đối tượng này
#     assert avatar_resource.public_id == fake_public_id
#     assert avatar_resource.version == fake_version
#     assert avatar_resource.format == fake_format
#
#     log_step("=> PASSED!")
