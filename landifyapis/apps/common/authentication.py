import logging

import jwt
from firebase_admin import auth
from rest_framework import authentication, exceptions

from apps.common.utils import firebase
from apps.users.models import User

logger = logging.getLogger(__name__)


class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Lớp xác thực tùy chỉnh cho Firebase.
    Xác thực Firebase ID Token và tìm hoặc tạo người dùng Django tương ứng.

    Lớp này sẽ trả về `None` nếu token không phải là một Firebase ID Token hợp lệ,
    cho phép Django REST Framework thử các lớp xác thực khác (ví dụ: Simple JWT).
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        id_token = auth_header.split(" ").pop()

        try:
            unverified_header = jwt.get_unverified_header(id_token)
            if "kid" not in unverified_header:
                return None
        except jwt.exceptions.DecodeError:
            return None

        try:
            decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Token Firebase không hợp lệ: {e}")

        uid = decoded_token.get("uid")
        if not uid:
            raise exceptions.AuthenticationFailed("Token Firebase hợp lệ nhưng không chứa UID.")

        try:
            user, created = User.objects.get_or_create(
                firebase_uid=uid,
                defaults={
                    "username": uid,
                    "email": decoded_token.get("email"),
                    "phone_number": decoded_token.get("phone_number"),
                    "is_active": True,
                    "is_phone_verified": bool(decoded_token.get("phone_number")),
                    # QUAN TRỌNG: User tạo từ Firebase mặc định là vai trò 'user'
                    "role": User.Role.USER,
                },
            )

            # Tạo UserProfile nếu user mới được tạo
            if created:
                from apps.users.models import UserProfile

                UserProfile.objects.create(user=user)

            return (user, None)

        except Exception as e:
            logger.error("Lỗi khi get_or_create user từ Firebase UID: %s", e)
            raise exceptions.AuthenticationFailed("Lỗi hệ thống khi xác thực người dùng.")
