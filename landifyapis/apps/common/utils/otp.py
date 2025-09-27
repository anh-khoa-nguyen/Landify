import random

from django.core.cache import cache


def generate_otp(length: int = 6) -> str:
    """Tạo một mã OTP số ngẫu nhiên."""
    return str(random.randint(10 ** (length - 1), 10**length - 1))


def save_otp_to_cache(key: str, otp: str):
    """Lưu OTP vào cache với thời gian hết hạn là 5 phút (300 giây)."""
    cache_key = f"otp_{key}"
    cache.set(cache_key, otp, timeout=300)


def verify_otp_from_cache(key: str, otp_code: str) -> bool:
    """Xác thực OTP từ cache. Trả về True nếu hợp lệ, False nếu không."""
    cache_key = f"otp_{key}"
    stored_otp = cache.get(cache_key)
    if stored_otp and stored_otp == otp_code:
        cache.delete(cache_key)  # OTP chỉ được dùng một lần
        return True
    return False
