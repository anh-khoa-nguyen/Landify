# landifys/authentication.py (PHIÊN BẢN CUỐI CÙNG)

from rest_framework import authentication, exceptions
from . import utils

class FirebaseDummyUser:
    @property
    def is_authenticated(self):
        return True

class FirebaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        try:
            id_token = auth_header.split(' ').pop()
            decoded_token = utils.verify_firebase_token(id_token)
            if not decoded_token:
                raise exceptions.AuthenticationFailed('Token không hợp lệ hoặc đã hết hạn.')

            # Gắn payload token vào request để các view có thể sử dụng
            request.firebase_user = decoded_token

            # Trả về một instance của lớp User giả của chúng ta.
            # Điều này sẽ gán một đối tượng vào `request.user` mà không gây lỗi.
            return (FirebaseDummyUser(), None)

        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))