import logging
import os
from typing import Any, Dict

import firebase_admin
from django.conf import settings
from firebase_admin import auth, credentials, firestore, messaging

from apps.users.models import User

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


def send_fcm_notification(
        user_id: int,
        title: str,
        body: str,
        data: Dict[str, str] = None
) -> bool:
    """Gửi một push notification đến các thiết bị của người dùng qua FCM."""
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK chưa được khởi tạo. Không thể gửi FCM.")
        return False

    try:
        # Lấy FCM token của người dùng từ Firestore
        db = firestore.client()
        user_doc = db.collection("users").document(str(user_id)).get()
        if not user_doc.exists:
            logger.warning(f"Không tìm thấy document user {user_id} trên Firestore để lấy FCM token.")
            return False

        fcm_token = user_doc.to_dict().get("fcmToken")
        if not fcm_token:
            logger.warning(f"User ID {user_id} không có FCM token. Không thể gửi thông báo.")
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            # Cấu hình cho Android để ưu tiên hiển thị thông báo
            android=messaging.AndroidConfig(
                priority="high",
            ),
            # Cấu hình cho Apple Push Notification Service
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        content_available=True,
                    ),
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f"Gửi FCM thành công cho user ID {user_id}: {response}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi FCM cho user ID {user_id}: {e}")
        return False


def create_firestore_chat_session(postgres_chat_id: int, user1: User, user2: User, listing_title: str) -> bool:
    """
    Tạo một document mới cho cuộc trò chuyện trên Firestore.
    Document này sẽ được client lắng nghe để hiển thị trong danh sách chat.
    """
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK chưa được khởi tạo. Không thể tạo phiên chat.")
        return False

    db = firestore.client()
    try:
        # ID của document trên Firestore sẽ là ID từ Postgres để dễ dàng tra cứu
        chat_doc_ref = db.collection("chats").document(str(postgres_chat_id))

        # === THAY ĐỔI QUAN TRỌNG: Tạo object chứa đầy đủ thông tin user ===
        user1_data = {
            "postgresId": user1.id,
            "firebaseUid": user1.firebase_uid,
            "fullName": user1.get_full_name() or user1.username,
            "avatarUrl": user1.profile.avatar.url if user1.profile.avatar else None,
            "isVerified": user1.is_identity_verified,
        }
        user2_data = {
            "postgresId": user2.id,
            "firebaseUid": user2.firebase_uid,
            "fullName": user2.get_full_name() or user2.username,
            "avatarUrl": user2.profile.avatar.url if user2.profile.avatar else None,
            "isVerified": user2.is_identity_verified,
        }
        # =================================================================

        chat_data = {
            "postgresId": postgres_chat_id,
            # Lưu lại một mảng các Firebase UID để truy vấn `array-contains`
            "participantUids": [user1.firebase_uid, user2.firebase_uid],
            # Lưu lại một map chứa thông tin chi tiết của 2 người
            "participants": {
                user1.firebase_uid: user1_data,
                user2.firebase_uid: user2_data,
            },
            "lastMessage": f"Cuộc trò chuyện về: {listing_title}",
            "lastMessageTimestamp": firestore.SERVER_TIMESTAMP,
            "unreadCount": {
                user1.firebase_uid: 0,
                user2.firebase_uid: 0,
            },
        }

        chat_doc_ref.set(chat_data)
        logger.info(f"Đã tạo phiên chat trên Firestore thành công cho Postgres Chat ID: {postgres_chat_id}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo phiên chat trên Firestore cho ID {postgres_chat_id}: {e}")
        return False

def create_firestore_call_session(
    channel_name: str,
    token: str,
    caller: User,
    receiver: User,
    is_video_call: bool
) -> bool:
    """
    Tạo một document mới cho một phiên gọi điện trên Firestore.
    Document này sẽ được client của người nhận lắng nghe.
    """
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK chưa được khởi tạo. Không thể tạo phiên gọi.")
        return False

    db = firestore.client()
    try:
        # ID của document trên Firestore sẽ là channel_name để dễ dàng tra cứu
        call_doc_ref = db.collection("active_calls").document(channel_name)

        caller_data = {
            "firebaseUid": caller.firebase_uid,
            "fullName": caller.get_full_name() or caller.username,
            "avatarUrl": caller.profile.avatar.url if caller.profile.avatar else None,
        }
        receiver_data = {
            "firebaseUid": receiver.firebase_uid,
            "fullName": receiver.get_full_name() or receiver.username,
            "avatarUrl": receiver.profile.avatar.url if receiver.profile.avatar else None,
        }

        call_data = {
            "channelName": channel_name,
            "token": token,
            "caller": caller_data,
            "receiver": receiver_data,
            "isVideoCall": is_video_call,
            "status": "ringing", # Trạng thái ban đầu
            "createdAt": firestore.SERVER_TIMESTAMP,
        }

        call_doc_ref.set(call_data)
        logger.info(f"Đã tạo phiên gọi trên Firestore thành công cho kênh: {channel_name}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo phiên gọi trên Firestore cho kênh {channel_name}: {e}")
        return False