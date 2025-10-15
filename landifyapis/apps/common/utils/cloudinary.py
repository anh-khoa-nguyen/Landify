import logging

import cloudinary.uploader

logger = logging.getLogger(__name__)


def delete_cloudinary_file(public_id: str):
    """Xóa một file trên Cloudinary bằng public_id của nó."""
    if not public_id:
        return
    try:
        cloudinary.uploader.destroy(public_id)
        logger.info("Đã xóa file trên Cloudinary với public_id: %s", public_id)
    except Exception as e:
        logger.error("Lỗi khi xóa file trên Cloudinary (public_id: %s): %s", public_id, e)
