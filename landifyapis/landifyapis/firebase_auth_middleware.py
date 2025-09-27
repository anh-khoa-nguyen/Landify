# landifyapis/firebase_auth_middleware.py
import traceback
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from firebase_admin import auth

from apps.users.models import User, UserProfile


@database_sync_to_async
def get_user_from_firebase_uid(uid):
    """
    Hàm bất đồng bộ để lấy hoặc tạo User Django từ Firebase UID.
    Đây là logic cốt lõi từ FirebaseAuthentication của bạn.
    """
    try:
        # Lấy thông tin user từ Firebase để điền vào defaults
        firebase_user = auth.get_user(uid)

        user, created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={
                "username": uid,  # Dùng UID làm username mặc định
                "email": getattr(firebase_user, 'email', None),
                "phone_number": getattr(firebase_user, 'phone_number', None),
                "is_active": True,
                "is_phone_verified": bool(getattr(firebase_user, 'phone_number', None)),
                "role": User.Role.USER,
            },
        )

        if created:
            UserProfile.objects.create(user=user)
            print(f"Created new Django user for Firebase UID: {uid}")

        return user
    except Exception as e:
        print(f"Error in get_user_from_firebase_uid: {e}")
        traceback.print_exc()
        return AnonymousUser()


class FirebaseTokenAuthMiddleware:
    """
    Middleware cho Channels để xác thực người dùng qua Firebase ID Token
    được gửi trong query string.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Lấy query string từ scope
        query_string = scope.get("query_string", b"").decode("utf-8")

        # Parse query string để lấy token
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            try:
                # Xác minh ID Token bằng Firebase Admin SDK
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']

                # Lấy hoặc tạo user Django tương ứng
                scope['user'] = await get_user_from_firebase_uid(uid)

            except Exception as e:
                # Nếu token không hợp lệ, gán AnonymousUser
                print(f"Firebase token verification failed: {e}")
                scope['user'] = AnonymousUser()
        else:
            # Nếu không có token, gán AnonymousUser
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)