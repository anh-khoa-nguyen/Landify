# landifyapis/asgi.py
import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Đặt os.environ và django.setup() lên đầu tiên
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "landifyapis.settings")
django.setup()

import apps.interactions.routing

# Bây giờ mới import các thành phần của Channels và các app Django
# vì Django đã được khởi tạo xong
from landifyapis.firebase_auth_middleware import FirebaseTokenAuthMiddleware

# # --- PHẦN DEBUG ---
# print("="*50)
# print(">>> ĐANG KIỂM TRA WEBSOCKET URL PATTERNS <<<")
# for pattern in apps.interactions.routing.websocket_urlpatterns:
#     print(f"  - Pattern: {pattern.pattern.pattern}")
# print("="*50)
# # --- KẾT THÚC DEBUG ---

# daphne -p 8000 landifyapis.asgi:application
# Lấy application HTTP sau khi đã setup
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        # Request HTTP thông thường sẽ được xử lý bởi Django
        "http": django_asgi_app,
        # Request WebSocket sẽ được xử lý bởi routing của Channels
        "websocket": FirebaseTokenAuthMiddleware(URLRouter(apps.interactions.routing.websocket_urlpatterns)),
    }
)
