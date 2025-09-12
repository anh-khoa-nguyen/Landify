import asyncio
import json
import requests
import websockets
from datetime import datetime, timedelta

# ==============================================================================
# === CẤU HÌNH: THAY THẾ BẰNG THÔNG TIN CỦA BẠN ===
# ==============================================================================

# Dùng URL ngrok để dễ dàng test
DJANGO_BASE_URL = "https://presumably-literate-bluejay.ngrok-free.app"

# Thông tin đăng nhập Firebase của 2 người dùng
# User A sẽ là người tạo lịch hẹn
# User B sẽ là chủ tin đăng (người nhận yêu cầu)
USER_A_EMAIL = "abb@gmail.com"
USER_A_PASSWORD = "123456"

USER_B_EMAIL = "abc@gmail.com"
USER_B_PASSWORD = "123456"

# Public ID của một tin đăng có sẵn (do User B sở hữu)
LISTING_PUBLIC_ID = "ONV45yQE"

# Web API Key của Firebase project
FIREBASE_WEB_API_KEY = "AIzaSyDH-pNSGbTUUbOMsReU46spQ4yv1NQkWsM"


# ==============================================================================
# === CÁC HÀM TIỆN ÍCH (Tương tự script trước) ===
# ==============================================================================

def get_firebase_id_token(email, password):
    """Lấy Firebase ID Token."""
    # ... (Giữ nguyên hàm này từ script full_chat_test.py)
    rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    try:
        response = requests.post(rest_api_url, data=payload)
        response.raise_for_status()
        return response.json()['idToken']
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi lấy Firebase ID Token cho {email}: {e.response.text}")
        return None


async def start_chat_session(user_token):
    """Bắt đầu cuộc trò chuyện để lấy chat_id."""
    # ... (Giữ nguyên hàm này từ script full_chat_test.py)
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


# ==============================================================================
# === CÁC HÀM MỚI CHO KỊCH BẢN NÀY ===
# ==============================================================================

def create_appointment(user_token, listing_public_id):
    """Gọi API để tạo một lịch hẹn mới."""
    api_url = f"{DJANGO_BASE_URL}/api/appointments/"
    headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}

    # Tạo một thời gian hẹn trong tương lai (ví dụ: 2 ngày sau)
    appointment_time = (datetime.now() + timedelta(days=2)).isoformat()

    data = {
        "listing_public_id": listing_public_id,
        "appointment_date": appointment_time,
        "note": "Tôi muốn xem nhà, vui lòng xác nhận."
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        appointment_data = response.json()
        print(f"✅ Tạo lịch hẹn thành công: ID = {appointment_data['id']}")
        return appointment_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tạo lịch hẹn: {e.response.text}")
        return None


def send_appointment_message(user_token, chat_id, appointment_id):
    """Gọi API để gửi tin nhắn yêu cầu hẹn gặp vào cuộc trò chuyện."""
    api_url = f"{DJANGO_BASE_URL}/api/chats/{chat_id}/send_appointment_request/"
    headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
    data = {"appointment_id": appointment_id}

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        message_data = response.json()
        print(f"✅ Gửi tin nhắn hẹn gặp thành công. Nội dung tin nhắn:")
        print(json.dumps(message_data, indent=2, ensure_ascii=False))
        return message_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi gửi tin nhắn hẹn gặp: {e.response.text}")
        return None


async def listen_for_messages(name, chat_id, token):
    """Một client WebSocket chỉ để lắng nghe tin nhắn."""
    if DJANGO_BASE_URL.startswith("https://"):
        base_ws_url = DJANGO_BASE_URL.replace("https://", "wss://")
    else:
        base_ws_url = DJANGO_BASE_URL.replace("http://", "ws://")
    uri = f"{base_ws_url}/api/ws/chat/{chat_id}/?token={token}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{name}] ✅ Đã kết nối và đang lắng nghe phòng chat {chat_id}...")
            try:
                # Lắng nghe trong 10 giây
                async for message in asyncio.timeout(websocket, timeout=10):
                    print(f"[{name}] 📥 Nhận được tin nhắn broadcast: {json.loads(message)}")
            except TimeoutError:
                print(f"[{name}] ⏳ Hết thời gian chờ tin nhắn.")
    except Exception as e:
        print(f"[{name}] ❌ Lỗi WebSocket: {e}")


# ==============================================================================
# === KỊCH BẢN TEST CHÍNH ===
# ==============================================================================

async def main():
    print("\n--- BƯỚC 1: LẤY FIREBASE ID TOKEN CHO 2 USER ---")
    user_a_token = get_firebase_id_token(USER_A_EMAIL, USER_A_PASSWORD)
    user_b_token = get_firebase_id_token(USER_B_EMAIL, USER_B_PASSWORD)
    if not all([user_a_token, user_b_token]): return

    print("\n--- BƯỚC 2: USER A TẠO MỘT LỊCH HẸN MỚI ---")
    appointment = create_appointment(user_a_token, LISTING_PUBLIC_ID)
    if not appointment: return
    appointment_id = appointment['id']

    print("\n--- BƯỚC 3: USER A BẮT ĐẦU CUỘC TRÒ CHUYỆN ĐỂ LẤY CHAT_ID ---")
    chat_info = await start_chat_session(user_a_token)
    if not chat_info: return
    chat_id = chat_info['chat_id']

    print(f"\n--- BƯỚC 4: CẢ 2 USER KẾT NỐI VÀO PHÒNG CHAT {chat_id} ĐỂ LẮNG NGHE ---")
    # Tạo task lắng nghe cho User B
    listener_task_b = asyncio.create_task(
        listen_for_messages("User B", chat_id, user_b_token)
    )
    # Tạo task lắng nghe cho User A
    listener_task_a = asyncio.create_task(
        listen_for_messages("User A", chat_id, user_a_token)
    )

    # Chờ 2 giây để đảm bảo cả hai client đã kết nối WebSocket
    await asyncio.sleep(2)

    print("\n--- BƯỚC 5: USER A GỬI TIN NHẮN YÊU CẦU HẸN GẶP QUA API ---")
    send_appointment_message(user_a_token, chat_id, appointment_id)

    # Chờ các task lắng nghe hoàn thành (sau 10 giây)
    await asyncio.gather(listener_task_a, listener_task_b)

    print("\n🎉 Kịch bản test hoàn tất! 🎉")
    print("Kiểm tra output để xem User A và B có nhận được tin nhắn thẻ hẹn gặp không.")


if __name__ == "__main__":
    asyncio.run(main())