import logging
from typing import IO, List  # <-- Thêm List

import cloudinary.uploader

from ..common.services import BusinessLogicError  # Giả sử bạn tạo file này
from . import models

logger = logging.getLogger(__name__)


def add_media_to_property(*, prop: models.Property, media_file: IO) -> models.PropertyMedia:
    try:
        upload_result = cloudinary.uploader.upload(media_file, resource_type="auto")
        media = models.PropertyMedia.objects.create(
            property=prop, url=upload_result["secure_url"], public_id=upload_result["public_id"]
        )
        return media
    except Exception as e:
        raise BusinessLogicError(f"Upload file thất bại: {e}")


def add_multiple_media_to_property(*, prop: models.Property, media_files: List[IO]) -> List[models.PropertyMedia]:
    """
    Tạo các bản ghi PropertyMedia từ một danh sách file upload.
    Việc upload thực tế sẽ do CloudinaryField xử lý khi .save() được gọi.
    """
    if not media_files:
        raise BusinessLogicError("Không có file nào được cung cấp.")

    instances_to_create = []
    for file in media_files:
        # Chỉ tạo instance trong bộ nhớ, chưa lưu vào DB
        instances_to_create.append(
            models.PropertyMedia(property=prop, url=file)  # Gán thẳng file vào trường `url` (CloudinaryField)
        )

    if not instances_to_create:
        raise BusinessLogicError("Không có file hợp lệ nào để xử lý.")

    try:
        created_instances = models.PropertyMedia.objects.bulk_create(instances_to_create)
        return created_instances
    except Exception as e:
        logger.error("Lỗi khi bulk_create PropertyMedia: %s", e)
        raise BusinessLogicError(f"Không thể lưu file media: {e}")
