import asyncio
import json

import firebase_admin
import requests
import websockets
from firebase_admin import credentials

# ==============================================================================
# === CẤU HÌNH: THAY THẾ BẰNG THÔNG TIN CỦA BẠN ===
# ==============================================================================

# URL của backend Django (thay bằng ngrok URL của bạn nếu cần)
DJANGO_BASE_URL = "https://presumably-literate-bluejay.ngrok-free.app"

# Thông tin đăng nhập Firebase của 2 người dùng bạn đã tạo
USER_A_EMAIL = "abb@gmail.com"
USER_A_PASSWORD = "123456"

USER_B_EMAIL = "abc@gmail.com"
USER_B_PASSWORD = "123456"

# Public ID của một tin đăng có sẵn để bắt đầu cuộc trò chuyện
LISTING_PUBLIC_ID = "ONV45yQE"  # Thay bằng public_id thật

# Web API Key của Firebase project (Lấy từ Firebase Console -> Project Settings)
FIREBASE_WEB_API_KEY = "AIzaSyDH-pNSGbTUUbOMsReU46spQ4yv1NQkWsM"  # Đây là key "web" của bạn

# ==============================================================================
# === KHỞI TẠO FIREBASE ADMIN SDK ===
# ==============================================================================
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK đã được khởi tạo.")
except Exception as e:
    print(f"❌ Lỗi khởi tạo Firebase Admin SDK: {e}")
    print("Hãy đảm bảo file serviceAccountKey.json nằm cùng thư mục.")
    exit()


# ==============================================================================
# === CÁC HÀM TIỆN ÍCH ===
# ==============================================================================


def get_firebase_id_token(email, password):
    """Mô phỏng việc đăng nhập để lấy Firebase ID Token."""
    rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    try:
        response = requests.post(rest_api_url, data=payload)
        response.raise_for_status()
        return response.json()["idToken"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi lấy Firebase ID Token cho {email}: {e.response.text}")
        return None


async def start_chat_session(user_token):
    """Gọi API /chats/start/ để lấy thông tin phòng chat."""
    api_url = f"{DJANGO_BASE_URL}/api/chats/start/"
    headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
    data = {"public_id": LISTING_PUBLIC_ID}

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        chat_info = response.json()
        print(f"✅ Lấy thông tin phòng chat thành công: {chat_info}")
        return chat_info
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi gọi API start_chat: {e.response.text}")
        return None


async def run_chat_client(name, chat_id, token, message_to_send):
    """Một client WebSocket để kết nối, gửi và nhận tin nhắn."""
    """Một client WebSocket để kết nối, gửi và nhận tin nhắn."""
    # Logic mới để xử lý cả http/ws và https/wss
    if DJANGO_BASE_URL.startswith("https://"):
        base_ws_url = DJANGO_BASE_URL.replace("https://", "wss://")
    else:
        base_ws_url = DJANGO_BASE_URL.replace("http://", "ws://")

        # SỬA LẠI ĐƯỜNG DẪN Ở ĐÂY ĐỂ KHỚP VỚI routing.py
    uri = f"{base_ws_url}/api/ws/chat/{chat_id}/?token={token}"

    print(f"[{name}] Đang kết nối tới: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{name}] ✅ Đã kết nối tới phòng chat {chat_id}")

            # Chờ một chút để client kia cũng kết nối
            await asyncio.sleep(2)

            # Gửi tin nhắn
            if message_to_send:
                payload = json.dumps({"message": message_to_send})
                await websocket.send(payload)
                print(f"[{name}] 📤 Gửi đi: {payload}")

            # Lắng nghe tin nhắn trong 5 giây
            try:
                async with asyncio.timeout(5):
                    async for message in websocket:
                        print(f"[{name}] 📥 Nhận được: {message}")
            except TimeoutError:
                print(f"[{name}] ⏳ Hết thời gian chờ tin nhắn.")

            print(f"[{name}] 🛑 Ngắt kết nối.")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[{name}] ❌ Kết nối bị từ chối bởi server: HTTP {e.status_code}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[{name}] ❌ Kết nối bị đóng: {e.code} - {e.reason}")
    # Bắt các lỗi chung khác
    except Exception as e:
        print(f"[{name}] ❌ Lỗi WebSocket không xác định: {e}")


# ==============================================================================
# === KỊCH BẢN TEST CHÍNH ===
# ==============================================================================


async def main():
    print("\n--- BƯỚC 1: LẤY FIREBASE ID TOKEN CHO 2 USER ---")
    user_a_token = get_firebase_id_token(USER_A_EMAIL, USER_A_PASSWORD)
    user_b_token = get_firebase_id_token(USER_B_EMAIL, USER_B_PASSWORD)

    if not all([user_a_token, user_b_token]):
        print("\nKhông thể lấy đủ token. Dừng test.")
        return

    print("\n--- BƯỚC 2: USER A BẮT ĐẦU CUỘC TRÒ CHUYỆN ---")
    chat_info = await start_chat_session(user_a_token)
    if not chat_info:
        print("\nKhông thể tạo phòng chat. Dừng test.")
        return

    # SỬA LẠI KEY Ở ĐÂY CHO KHỚP VỚI RESPONSE MỚI CỦA API
    postgres_chat_id = chat_info["chat_id"]

    print("\n--- BƯỚC 3: CẢ 2 USER CÙNG KẾT NỐI VÀO PHÒNG CHAT ---")
    print("User A sẽ gửi tin nhắn, User B sẽ lắng nghe.")

    # Tạo 2 task chạy song song
    task_a = asyncio.create_task(
        run_chat_client("User A", postgres_chat_id, user_a_token, "Chào User B, tôi là User A đây!")
    )
    task_b = asyncio.create_task(run_chat_client("User B", postgres_chat_id, user_b_token, None))

    # Chờ cả hai task hoàn thành
    await asyncio.gather(task_a, task_b)

    print("\n🎉 Kịch bản test hoàn tất! 🎉")
    print("Hãy kiểm tra console của Django và database để xem kết quả.")


if __name__ == "__main__":
    asyncio.run(main())
