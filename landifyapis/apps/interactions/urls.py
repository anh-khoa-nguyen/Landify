from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views

router = DefaultRouter()

router.register(r"chats", views.ChatViewSet, basename="chat")

router.register(r"appointments", views.AppointmentViewSet, basename="appointment")
# router.register(r'wishlists', views.WishlistViewSet, basename='wishlist')
router.register(r"cooperations", views.CooperationViewSet, basename="cooperation")

chats_router = routers.NestedDefaultRouter(router, r"chats", lookup="chat")
chats_router.register(r"messages", views.MessageViewSet, basename="chat-messages")

urlpatterns = [
    path("chats/start/", views.StartChatView.as_view(), name="start-chat"),
    path("chats/start-with-user/", views.StartChatWithUserView.as_view(), name="start-chat-with-user"),
    path(
        "chats/<int:chat_pk>/send_appointment_request/",
        views.SendAppointmentRequestView.as_view(),
        name="chat-send-appointment",
    ),
    path("", include(router.urls)),
    path("", include(chats_router.urls)),
]
