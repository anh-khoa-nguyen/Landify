from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from firebase_admin import firestore
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import perms
from apps.common.docs import interactions_docs
from apps.common.utils import hashids  # <-- Import hashids
from apps.common.utils.hashids import hashids
from apps.listings.models import Listing
from apps.properties.models import Property
from apps.users.models import User

from ..common.services import BusinessLogicError
from ..common.utils.hashids import get_object_from_public_id_or_404
from . import services as interactions_services
from .models import Appointment, Chat, Cooperation, Message, Review, Wishlist
from .serializers import (
    AppointmentSerializer,
    ChatDetailSerializer,
    CooperationSerializer,
    MessageSerializer,
    ReviewSerializer,
    WishlistSerializer,
)
from .services import (
    CooperationActionError,
    create_group_chat,
    get_or_create_private_chat,
    respond_to_cooperation_request,
)

# ==============================================================================
# PRIMARY INTERACTION VIEWSETS
# ==============================================================================
# Các ViewSet này quản lý các nghiệp vụ tương tác chính như Đặt lịch,
# Đánh giá, và Hợp tác môi giới.


@interactions_docs.appointment_viewset_schema
class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet cho việc quản lý lịch hẹn."""

    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return Appointment.objects.all()
        return Appointment.objects.filter(Q(user=user) | Q(listing__user=user)).distinct()

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [perms.IsIdentityVerified]
        elif self.action == 'update_status':
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [permissions.IsAuthenticated]

        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @interactions_docs.update_appointment_status_schema
    @action(methods=["patch"], detail=True, url_path="update-status")
    def update_status(self, request, pk=None):
        appointment = self.get_object()
        new_status = request.data.get("status")

        if not new_status:
            return Response({"error": "Trường 'status' là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        actor = request.user
        listing_owner = appointment.listing.user
        requester = appointment.user

        can_confirm_or_complete = (actor == listing_owner or actor.role == User.Role.ADMIN)
        can_cancel = (actor == listing_owner or actor == requester or actor.role == User.Role.ADMIN)

        is_allowed = False
        if new_status in [Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED]:
            if can_confirm_or_complete:
                is_allowed = True
        elif new_status == Appointment.Status.CANCELLED:
            if can_cancel:
                is_allowed = True

        if not is_allowed:
            return Response(
                {"detail": "Bạn không có quyền thực hiện hành động này trên lịch hẹn này."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            updated_appointment = interactions_services.update_appointment_status(
                appointment=appointment, new_status=new_status, actor=request.user
            )

            serializer = self.get_serializer(updated_appointment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@interactions_docs.wishlist_viewset_schema  # Giả định bạn sẽ tạo doc này
class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý các đánh giá (Review) cho Bất động sản.
    URL: /api/reviews/ (cho việc tạo)
    URL: /api/properties/{property_pk}/reviews/ (cho việc xem)
    """

    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [perms.IsIdentityVerified()]
        return [perms.IsOwnerOrAdmin()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.kwargs.get("public_id_public_id"):
            public_id = self.kwargs.get("public_id_public_id")
            listing = get_object_from_public_id_or_404(Listing.objects, public_id)
            context["property"] = listing.property
        return context

    def get_queryset(self):
        queryset = Review.objects.select_related("user__profile").all()

        public_id = self.kwargs.get("public_id_public_id")
        if public_id:
            listing = get_object_from_public_id_or_404(Listing.objects, public_id)
            return queryset.filter(property=listing.property)

        return queryset

    def perform_create(self, serializer):
        public_id = self.kwargs.get("public_id_public_id")
        if not public_id:
            raise serializers.ValidationError("URL không hợp lệ, thiếu ID của tin đăng.")

        listing = get_object_from_public_id_or_404(Listing.objects, public_id)
        prop = listing.property

        user_latitude = serializer.validated_data.get("latitude")
        user_longitude = serializer.validated_data.get("longitude")

        interactions_services.rate_property_and_update_score(
            user=self.request.user,
            prop=prop,
            serializer=serializer,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
        )
        return


class CooperationViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý luồng Hợp tác môi giới.
    - Môi giới (agent) có thể tạo yêu cầu (create).
    - Chủ tin đăng (owner) có thể xem và phản hồi (list, retrieve, respond).
    """

    serializer_class = CooperationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Cooperation.objects.filter(Q(agent=user) | Q(owner=user)).select_related(
            "listing", "agent__profile", "owner__profile"
        )

    def perform_create(self, serializer):
        listing = serializer.validated_data.pop('listing_public_id')

        agent = self.request.user
        owner = listing.user

        if agent == owner:
            raise serializers.ValidationError("Bạn không thể tự gửi yêu cầu hợp tác cho chính mình.")

        serializer.save(listing=listing, agent=agent, owner=owner)

    @action(methods=["post"], detail=True, url_path="respond")
    def respond(self, request, pk=None):
        cooperation = self.get_object()

        action_type = request.data.get("action")
        reason = request.data.get("reason")

        try:
            updated_cooperation = interactions_services.respond_to_cooperation_request(
                cooperation=cooperation, actor=request.user, action=action_type, reason=reason
            )
        except CooperationActionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(updated_cooperation)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==============================================================================
# CHAT & MESSAGING SYSTEM VIEWS
# ==============================================================================
# Các View và ViewSet này tạo nên toàn bộ API cho hệ thống trò chuyện.


class StartChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        public_id = request.data.get("public_id")
        if not public_id:
            return Response({"error": "public_id là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            listing = get_object_from_public_id_or_404(Listing.objects.select_related("user"), public_id)
        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        user1 = request.user
        user2 = listing.user

        if user1 == user2:
            return Response({"error": "Bạn không thể tự chat với chính mình."}, status=status.HTTP_400_BAD_REQUEST)

        chat_obj, created = get_or_create_private_chat(user1=user1, user2=user2, listing=listing)

        return Response(
            {
                "chat_id": chat_obj.id,
            },
            status=status.HTTP_200_OK,
        )


class ChatViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet để xem danh sách và chi tiết các cuộc trò chuyện.
    Chỉ cho phép các hành động đọc (list, retrieve).
    """

    serializer_class = ChatDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"  # Hoặc 'id'

    def get_queryset(self):
        user = self.request.user
        return user.chats.all().prefetch_related("participants", "listing").order_by("-last_message_timestamp")


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API View để lấy danh sách tin nhắn cũ của một cuộc trò chuyện.
    Chỉ cho phép đọc (GET list).
    """

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs.get("chat_pk")

        appointment_queryset = Appointment.objects.all().select_related("listing")
        cooperation_queryset = Cooperation.objects.all().select_related("listing", "agent")

        return Message.objects.filter(chat_id=chat_id, chat__participants=self.request.user).prefetch_related(
            GenericPrefetch(
                "linked_object",
                querysets=[
                    appointment_queryset,
                    cooperation_queryset,
                ],
            )
        )


class SendAppointmentRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_pk=None):
        appointment_id = request.data.get("appointment_id")

        chat = get_object_or_404(Chat, pk=chat_pk, participants=request.user)
        appointment = get_object_or_404(Appointment, pk=appointment_id)

        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            message_type=Message.MessageType.INTERACTIVE_CARD,
            linked_object=appointment,
            content=f"Yêu cầu hẹn gặp cho: {appointment.listing.title}",
        )
        chat.last_message_timestamp = message.created_date
        chat.save()

        channel_layer = get_channel_layer()

        serializer_context = {"request": request}

        message_data = MessageSerializer(message).data

        async_to_sync(channel_layer.group_send)(f"chat_{chat_pk}", {"type": "chat_message", "message": message_data})

        return Response(message_data, status=status.HTTP_201_CREATED)
