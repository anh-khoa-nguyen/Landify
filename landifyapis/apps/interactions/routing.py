# apps/interactions/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"api/ws/chat/(?P<chat_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
]
