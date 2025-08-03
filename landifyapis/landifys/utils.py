from django.utils.html import format_html
from django.urls import reverse
from twilio.rest import Client
from django.conf import settings
from datetime import datetime
import random
from django.core.cache import cache
import requests

def send_sms(to_phone_number, message_body):
    """
    Gửi tin nhắn SMS qua Twilio.

    Args:
        to_phone_number (str): Số điện thoại người nhận (bao gồm mã quốc gia, ví dụ: +848xxxxxxxx).
        message_body (str): Nội dung tin nhắn cần gửi.

    Returns:
        dict: Thông tin phản hồi sau khi gửi SMS thành công.
    """
    try:
        # Khởi tạo Client của Twilio
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Gửi tin nhắn
        message = twilio_client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )

        # Trả về thông tin phản hồi
        return {"message": "SMS sent successfully", "sid": message.sid}

    except Exception as e:
        # Trường hợp lỗi xảy ra
        return {"message": "Failed to send SMS", "error": str(e)}


def generate_otp(length=6):
    """Tạo một mã OTP số ngẫu nhiên."""
    return str(random.randint(10 ** (length - 1), 10 ** length - 1))


def save_otp_to_cache(user_id, otp):
    """Lưu OTP vào cache với thời gian hết hạn là 5 phút (300 giây)."""
    cache_key = f'otp_{user_id}'
    cache.set(cache_key, otp, timeout=300)


def verify_otp_from_cache(user_id, otp_code):
    """
    Xác thực OTP từ cache.
    Trả về True nếu hợp lệ, False nếu không.
    """
    cache_key = f'otp_{user_id}'
    stored_otp = cache.get(cache_key)

    if stored_otp and stored_otp == otp_code:
        # OTP hợp lệ, xóa khỏi cache để không thể sử dụng lại
        cache.delete(cache_key)
        return True
    return False

# ============= Identify Verify ===============
def call_fpt_idr_api(id_card_image_file):
    """
    Gọi API FPT ID Recognition để trích xuất thông tin từ ảnh CCCD.
    """
    url = 'https://api.fpt.ai/vision/idr/vnm'
    headers = {'api-key': settings.FPT_AI_API_KEY}
    files = {'image': id_card_image_file.read()}

    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    return response.json()


def call_fpt_liveness_api(video_file, id_card_image_data):
    url = 'https://api.fpt.ai/dmp/liveness/v3'
    headers = {'api-key': settings.FPT_AI_API_KEY}

    files = {
        'video': ('video.mp4', video_file.read(), 'application/octet-stream'),
        'cmnd': ('id_card.jpg', id_card_image_data, 'application/octet-stream')
    }

    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    return response.json()