from typing import IO, Any, Dict
from datetime import date, datetime
import time

from django.core.cache import cache
from django.db import transaction
from django.conf import settings

from agora_token_builder import RtcTokenBuilder

from apps.common.services import BusinessLogicError, EkycError
from apps.common.utils import ekyc, otp, sms
from apps.common.func import fengshui
from apps.users.models import User, UserProfile

def request_phone_otp(*, user: User):
    """Xử lý toàn bộ quy trình gửi mã OTP xác thực SĐT."""
    if not user.phone_number:
        raise BusinessLogicError("Bạn chưa cập nhật số điện thoại.")

    otp_code = otp.generate_otp()
    otp.save_otp_to_cache(user.phone_number, otp_code)
    message_body = f"[Landify] Mã xác thực của bạn là: {otp_code}. Mã có hiệu lực trong 5 phút."
    sms_response = sms.send_sms(user.phone_number, message_body)

    if "error" in sms_response:
        raise BusinessLogicError(f"Không thể gửi mã OTP đến {user.phone_number}. Vui lòng thử lại sau.")


def verify_phone_otp(*, user: User, otp_code: str) -> bool:
    if otp.verify_otp_from_cache(user.phone_number, otp_code):
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
        return True
    return False


def process_id_card_verification(*, user: User, id_card_image: IO) -> Dict[str, Any]:
    """Thực hiện bước 1 của eKYC: Đọc thông tin CCCD, lưu cache và cập nhật DB."""
    try:
        ocr_data = ekyc.call_cccd_ocr_api(id_card_image)
        if not ocr_data or not ocr_data.get("ID_number"):
            raise EkycError("Không thể đọc thông tin từ ảnh CCCD. Vui lòng thử lại với ảnh rõ nét hơn.")

        #extracted_data = idr_response.get("data")[0]

        with transaction.atomic():
            cache.set(f"ekyc_ocr_data_{user.id}", ocr_data, timeout=86400)

            user.is_id_card_verified = True
            profile = user.profile

            profile.id_card_number = ocr_data.get('ID_number')
            profile.nationality = ocr_data.get('Nationality') or "Việt Nam" # Gán mặc định nếu rỗng
            profile.home_town = ocr_data.get('Place_of_origin')
            profile.address = ocr_data.get('Place_of_residence')

            # address_entities = extracted_data.get('address_entities', {})
            # if address_entities and isinstance(address_entities, dict):
            #     # Ưu tiên lấy tỉnh/thành phố, nếu không có thì lấy quận/huyện
            #     province = address_entities.get('province')
            #     district = address_entities.get('district')
            #     if province:
            #         profile.location = province
            #     elif district:
            #         profile.location = district

            gender_str = ocr_data.get('Gender', '').lower()
            if gender_str == 'nam':
                profile.gender = User.Gender.MALE
            elif gender_str == 'nữ':
                profile.gender = User.Gender.FEMALE

            dob_str = ocr_data.get('Date_of_birth')
            if dob_str:
                try:
                    profile.date_of_birth = datetime.strptime(dob_str, "%d/%m/%Y").date()
                except ValueError:
                    pass

            full_name = ocr_data.get('Name', '').strip()
            if full_name:
                name_parts = full_name.split(' ')
                if len(name_parts) > 1:
                    # Lấy từ đầu tiên làm Họ (first_name)
                    user.first_name = name_parts[0]
                    # Các từ còn lại làm Tên đệm và Tên (last_name)
                    user.last_name = ' '.join(name_parts[1:])
                else:
                    # Nếu chỉ có một từ, coi đó là Tên (last_name) và Họ (first_name) rỗng
                    # Hoặc bạn có thể gán nó cho first_name tùy theo quy ước
                    user.first_name = ''
                    user.last_name = full_name

            user.save(update_fields=['is_id_card_verified', 'first_name', 'last_name'])
            profile.save(update_fields=[
                'id_card_number', 'nationality', 'home_town',
                'address', 'gender', 'date_of_birth',
            ])

        return ocr_data
    except Exception as e:
        raise EkycError(f"Đã có lỗi xảy ra trong quá trình xử lý ảnh: {e}")


def complete_ekyc_liveness_check(*, user: User, video_file: IO):
    """Thực hiện bước 2 của eKYC: xác thực người thật và so khớp khuôn mặt."""
    ocr_data_from_cache = cache.get(f"ekyc_ocr_data_{user.id}")
    if not ocr_data_from_cache:
        raise EkycError("Phiên xác thực đã hết hạn hoặc không tồn tại. Vui lòng bắt đầu lại từ bước 1.")

    try:
        liveness_response = ekyc.call_liveness_verification_api(video_file, ocr_data_from_cache)
    except Exception as e:
        raise EkycError(f"Không thể kết nối đến dịch vụ xác thực: {e}")

    is_verified = liveness_response.get("verified")

    if is_verified is True:
        # Nếu xác thực thành công, cập nhật trạng thái và xóa cache
        with transaction.atomic():
            user.is_identity_verified = True
            user.save(update_fields=["is_identity_verified"])
            cache.delete(f"ekyc_ocr_data_{user.id}")
    else:
        # Nếu xác thực thất bại, lấy message từ API và ném lỗi
        error_message = liveness_response.get("message", "Xác thực không thành công. Vui lòng thử lại.")
        raise EkycError(error_message)

def generate_agora_token(*, channel_name: str, uid: int) -> Dict[str, Any]:
    """Tạo token cho dịch vụ gọi video Agora."""
    if not channel_name:
        raise BusinessLogicError("channelName là bắt buộc.")

    app_id = settings.AGORA_APP_ID
    app_certificate = settings.AGORA_APP_CERTIFICATE
    expire_time_in_seconds = 3600
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expire_time_in_seconds

    ROLE_PUBLISHER = 1  # Vai trò của người phát sóng (broadcaster)

    try:
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            channel_name,
            uid,
            # VVV SỬA LẠI CÁCH GỌI Ở ĐÂY VVV
            # Sử dụng hằng số đã được import trực tiếp
            ROLE_PUBLISHER,
            privilege_expired_ts
        )
        return {"token": token, "uid": uid}
    except Exception as e:
        raise BusinessLogicError(f"Lỗi tạo token Agora: {e}")

def get_feng_shui_analysis(*, property_direction_name: str, date_of_birth: date) -> Dict[str, Any]:
    """Thực hiện phân tích phong thủy dựa trên hướng nhà và ngày sinh."""
    if not property_direction_name:
        raise BusinessLogicError("Bất động sản chưa có thông tin về hướng để phân tích.")
    if not date_of_birth:
        raise BusinessLogicError("Ngày sinh không hợp lệ.")

    birth_year = date_of_birth.year
    user_menh = fengshui.calculate_menh(birth_year=birth_year)
    if not user_menh:
        raise BusinessLogicError(f"Không thể xác định Mệnh cho năm sinh {birth_year}.")

    analysis_result = fengshui.analyze_feng_shui_rules(user_menh=user_menh, property_direction=property_direction_name)

    return {
        "user_menh_element": user_menh,
        "property_direction": property_direction_name,
        "compatibility_score": analysis_result.get("score", 0),
        "analysis": analysis_result.get("analysis", "Không có phân tích chi tiết."),
    }
