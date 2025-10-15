#!/usr/bin/env python3
import json
import sys

import requests

# =======================================================================
# == CẤU HÌNH
# =======================================================================
# Dán Web API Key bạn đã lấy từ Firebase Console vào đây
FIREBASE_WEB_API_KEY = "AIzaSyDH-pNSGbTUUbOMsReU46spQ4yv1NQkWsM"  # <<< THAY THẾ BẰNG KEY CỦA BẠN

# Số điện thoại TEST đã được thêm vào Firebase Authentication
# QUAN TRỌNG: Phải ở định dạng E.164
PHONE_NUMBER = "+84862465874"

# Mã OTP cố định cho số điện thoại TEST
TEST_OTP_CODE = "123456"

# Endpoints của Google Identity Platform API
SEND_OTP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendVerificationCode?key={FIREBASE_WEB_API_KEY}"
VERIFY_OTP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPhoneNumber?key={FIREBASE_WEB_API_KEY}"


# =======================================================================
# == HÀM CHÍNH
# =======================================================================
def get_phone_id_token_auto():
    """
    Tự động thực hiện luồng đăng nhập bằng SĐT test và OTP cố định.
    """
    print("--- Trình tạo Firebase ID Token TỰ ĐỘNG bằng SĐT Test ---")
    print(f"INFO: Sử dụng SĐT Test: {PHONE_NUMBER} và OTP: {TEST_OTP_CODE}")

    try:
        # ----------------------------------------------------
        # -- BƯỚC 1: Lấy sessionInfo
        # ----------------------------------------------------
        send_otp_payload = {"phoneNumber": PHONE_NUMBER}

        print("INFO: Bước 1/2 - Đang lấy sessionInfo từ Firebase...")
        response_step1 = requests.post(SEND_OTP_URL, json=send_otp_payload)
        response_step1.raise_for_status()

        response_data_step1 = response_step1.json()
        session_info = response_data_step1.get("sessionInfo")

        if not session_info:
            print("\n❌ LỖI: Không nhận được sessionInfo. Phản hồi:")
            print(response_data_step1)
            return

        print("✅ OK: Lấy sessionInfo thành công.")

        # ----------------------------------------------------
        # -- BƯỚC 2: Gửi sessionInfo và OTP cố định để lấy idToken
        # ----------------------------------------------------
        verify_otp_payload = {"sessionInfo": session_info, "code": TEST_OTP_CODE}

        print("\nINFO: Bước 2/2 - Đang xác thực với OTP cố định...")
        response_step2 = requests.post(VERIFY_OTP_URL, json=verify_otp_payload)
        response_step2.raise_for_status()

        response_data_step2 = response_step2.json()
        id_token = response_data_step2.get("idToken")

        if id_token:
            print("\n======================================================")
            print("✅ HOÀN TẤT! Dưới đây là ID Token của bạn:")
            print("======================================================")
            print(f"\n{id_token}\n")
            print("------------------------------------------------------")
            print(f"💡 Token này thuộc về user có SĐT: {response_data_step2.get('phoneNumber')}")
            print("   Dùng token này làm Bearer Token trong Postman.")
            print("   Token có hiệu lực trong 1 giờ.")
            print("======================================================")
        else:
            print("\n❌ LỖI: Không nhận được ID Token. Phản hồi:")
            print(response_data_step2)

    except requests.exceptions.HTTPError as e:
        error_data = e.response.json().get("error", {})
        error_message = error_data.get("message", "Lỗi không xác định.")
        print(f"\n❌ LỖI API ({e.response.status_code}): {error_message}")
        print("   Vui lòng kiểm tra lại SĐT Test, OTP, và Web API Key.")
        print("   Lưu ý: SĐT Test phải được thêm thủ công trong Firebase Console.")
    except Exception as e:
        print(f"\n❌ LỖI KHÔNG XÁC ĐỊNH: {e}")


# --- Điểm bắt đầu thực thi script ---
if __name__ == "__main__":
    if "AIzaSyDH-aaa" in FIREBASE_WEB_API_KEY:
        print("⚠️ CẢNH BÁO: Bạn đang sử dụng Web API Key mặc định.")
        print("   Vui lòng thay thế FIREBASE_WEB_API_KEY bằng key thật trong file script.")
        sys.exit(1)

    get_phone_id_token_auto()
