from django.conf import settings
from django.http import Http404  # <-- THÊM IMPORT NÀY
from hashids import Hashids

# Khởi tạo đối tượng hashids một lần duy nhất và có thể tái sử dụng ở mọi nơi
hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)


def decode_public_id(public_id_str: str) -> int | None:
    """
    Giải mã một public_id (chuỗi) thành ID thật (số nguyên).
    Trả về None nếu giải mã thất bại.
    """
    decoded_ids = hashids.decode(public_id_str)
    if not decoded_ids:
        return None
    return decoded_ids[0]


def get_object_from_public_id_or_404(model_manager, public_id_str: str):
    """
    Một hàm tiện ích kết hợp việc giải mã public_id và lấy đối tượng từ DB.
    """
    real_pk = decode_public_id(public_id_str)

    if real_pk is None:
        raise Http404("ID không hợp lệ.")

    try:
        # Dùng `select_related` hoặc `prefetch_related` nếu cần tối ưu
        return model_manager.get(pk=real_pk)
    except model_manager.model.DoesNotExist:
        raise Http404(f"Không tìm thấy đối tượng {model_manager.model.__name__}.")
