from .cloudinary import delete_cloudinary_file
from .ekyc import call_cccd_ocr_api, call_liveness_verification_api
from .firebase import initialize_firebase_sdk, send_firestore_notification, verify_firebase_token
from .otp import generate_otp, save_otp_to_cache, verify_otp_from_cache
from .sms import send_sms

# Khởi tạo Firebase SDK một lần khi ứng dụng Django khởi động
initialize_firebase_sdk()
