import os
from typing import Any, Dict

import firebase_admin
from django.conf import settings
from firebase_admin import auth, credentials, firestore

import logging
logger = logging.getLogger(__name__)

def initialize_firebase_sdk():
    """
    Hàm khởi tạo Firebase Admin SDK.
    Được gọi một lần duy nhất từ utils/__init__.py.
    """
    if not firebase_admin._apps:
        try:
            service_account_key_path = os.path.join(settings.BASE_DIR, "serviceAccountKey.json")
            cred = credentials.Certificate(service_account_key_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK đã được khởi tạo thành công.")
        except Exception as e:
            logger.critical("Không thể khởi tạo Firebase Admin SDK. Lỗi: %s", e)


def verify_firebase_token(id_token: str) -> Dict[str, Any] | None:
    """Xác minh Firebase ID Token bằng Admin SDK."""
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK chưa được khởi tạo. Lệnh verify_firebase_token thất bại.")
        return None
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.warning("Lỗi xác thực Firebase token: %s", e)
        return None


def send_firestore_notification(
    user_id: int, category: str, title: str, content: str, related_item: Dict[str, Any] = None
) -> bool:
    """Tạo một document thông báo mới trên Firestore cho một người dùng cụ thể."""
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK chưa được khởi tạo. Không thể gửi thông báo.")
        return False

    db = firestore.client()
    try:
        user_uid = str(user_id)
        notification_ref = db.collection("users").document(user_uid).collection("notifications").document()
        notification_data = {
            "category": category,
            "title": title,
            "content": content,
            "is_read": False,
            "created_at": firestore.SERVER_TIMESTAMP,
            "related_item": related_item or {},
        }
        notification_ref.set(notification_data)
        logger.info("Đã gửi thông báo Firestore thành công cho user ID: %s", user_id)
        return True
    except Exception as e:
        logger.error("Lỗi khi gửi thông báo Firestore cho user ID %s: %s", user_id, e)
        return False
