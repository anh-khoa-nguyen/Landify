from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework import permissions, serializers, status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.docs import interactions_docs
from apps.common import perms
from apps.users.models import User
from apps.properties.models import Property
from apps.listings.models import Listing
from apps.common.utils.hashids import hashids

from .models import Wishlist, Review, Appointment, Chat, Cooperation, Message
from . import services as interactions_services
from .serializers import (AppointmentSerializer, WishlistSerializer
, ReviewSerializer, ChatDetailSerializer, CooperationSerializer, MessageSerializer)

from ..common.services import BusinessLogicError
from .services import respond_to_cooperation_request, CooperationActionError, get_or_create_private_chat, create_group_chat
from apps.common.utils import hashids # <-- Import hashids
from ..common.utils.hashids import get_object_from_public_id_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from firebase_admin import firestore

# @interactions_docs.wishlist_viewset_schema
# class WishlistViewSet(viewsets.ModelViewSet):
#     """ViewSet cho danh sách yêu thích của người dùng."""
#
#     serializer_class = WishlistSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_queryset(self):
#         return Wishlist.objects.filter(user=self.request.user)
#
#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)

@interactions_docs.appointment_viewset_schema
class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet cho việc quản lý lịch hẹn."""

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return Appointment.objects.all()
        return Appointment.objects.filter(Q(user=user) | Q(listing__user=user)).distinct()

    def get_permissions(self):
        if self.action == "create":
            return [perms.IsIdentityVerified()]
        return [perms.IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @interactions_docs.update_appointment_status_schema
    @action(methods=["patch"], detail=True, url_path="update-status")
    def update_status(self, request, pk=None):
        appointment = self.get_object()
        new_status = request.data.get("status")

        if not new_status:
            return Response({"error": "Trường 'status' là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_appointment = interactions_services.update_appointment_status(
                appointment=appointment, new_status=new_status, actor=request.user
            )

            serializer = self.get_serializer(updated_appointment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


@interactions_docs.wishlist_viewset_schema  # Giả định bạn sẽ tạo doc này
class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý các đánh giá (Review) cho Bất động sản.
    URL: /api/reviews/ (cho việc tạo)
    URL: /api/properties/{property_pk}/reviews/ (cho việc xem)
    """
    serializer_class = ReviewSerializer

    def get_permissions(self):
        # Ai cũng có thể xem đánh giá
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        # Chỉ người dùng đã xác thực danh tính mới được tạo đánh giá
        if self.action == 'create':
            return [perms.IsIdentityVerified()]
        # Chỉ chủ sở hữu đánh giá hoặc admin mới được sửa/xóa
        return [perms.IsOwnerOrAdmin()]

    def get_serializer_context(self):
        """
        Ghi đè để thêm 'property' vào context cho serializer.
        """
        context = super().get_serializer_context()
        if self.kwargs.get('public_id_public_id'):
            public_id = self.kwargs.get('public_id_public_id')
            listing = get_object_from_public_id_or_404(Listing.objects, public_id)
            context['property'] = listing.property
        return context

    def get_queryset(self):
        """
        Nếu URL có property_pk, chỉ hiển thị review của BĐS đó.
        """
        queryset = Review.objects.select_related('user__profile').all()

        public_id = self.kwargs.get('public_id_public_id')
        if public_id:
            listing = get_object_from_public_id_or_404(Listing.objects, public_id)
            return queryset.filter(property=listing.property)

        return queryset

    def perform_create(self, serializer):
        public_id = self.kwargs.get('public_id_public_id')
        if not public_id:
            raise serializers.ValidationError("URL không hợp lệ, thiếu ID của tin đăng.")

        listing = get_object_from_public_id_or_404(Listing.objects, public_id)
        prop = listing.property
        # =================
        interactions_services.rate_property_and_update_score(
            user=self.request.user,
            prop=prop,
            serializer=serializer
        )
        return

#========================================================
class StartChatView(APIView):
    """
    API để bắt đầu hoặc lấy thông tin một cuộc trò chuyện.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        public_id = request.data.get('public_id')
        if not public_id:
            return Response({'error': 'public_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            listing = get_object_from_public_id_or_404(
                Listing.objects.select_related('user'),
                public_id
            )
        except Http404 as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

        user1 = request.user
        user2 = listing.user

        if user1 == user2:
            return Response({'error': 'Bạn không thể tự chat với chính mình.'}, status=status.HTTP_400_BAD_REQUEST)

        chat_obj, created = get_or_create_private_chat(user1=user1, user2=user2, listing=listing)

        return Response({
            'chat_id': chat_obj.id,
        }, status=status.HTTP_200_OK)

class ChatDetailView(generics.RetrieveAPIView):
    """
    API View để lấy chi tiết một cuộc trò chuyện.
    Chỉ những người tham gia trong cuộc trò chuyện mới có quyền xem.
    """
    queryset = Chat.objects.prefetch_related(
        'users__profile', # Lấy tất cả user và profile của họ
        'listing__property__media' # Lấy tin đăng và các media liên quan
    ).all()
    serializer_class = ChatDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """
        Ghi đè để đảm bảo người dùng chỉ có thể truy cập
        vào các cuộc trò chuyện mà họ là thành viên.
        """
        return super().get_queryset().filter(users=self.request.user)

class ChatViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet để xem danh sách và chi tiết các cuộc trò chuyện.
    Chỉ cho phép các hành động đọc (list, retrieve).
    """
    serializer_class = ChatDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk' # Hoặc 'id'

    def get_queryset(self):
        """
        Ghi đè để đảm bảo người dùng chỉ có thể truy cập
        vào các cuộc trò chuyện mà họ là thành viên.
        """
        user = self.request.user
        return user.chats.all().prefetch_related('participants', 'listing').order_by('-last_message_timestamp')

class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API View để lấy danh sách tin nhắn cũ của một cuộc trò chuyện.
    Chỉ cho phép đọc (GET list).
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs.get('chat_pk')

        # Định nghĩa các queryset cho prefetch
        appointment_queryset = Appointment.objects.all().select_related('listing')
        cooperation_queryset = Cooperation.objects.all().select_related('listing', 'agent')

        return Message.objects.filter(
            chat_id=chat_id,
            chat__participants=self.request.user
        ).prefetch_related(
            # Cung cấp querysets cho GenericPrefetch
            GenericPrefetch(
                'linked_object',
                querysets=[
                    appointment_queryset,
                    cooperation_queryset,
                ]
            )
        )
#========================================================
class SendAppointmentRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_pk=None):
        appointment_id = request.data.get('appointment_id')

        # 1. Lấy các object cần thiết và kiểm tra quyền
        chat = get_object_or_404(Chat, pk=chat_pk, participants=request.user)
        appointment = get_object_or_404(Appointment, pk=appointment_id)

        # 2. Tạo tin nhắn trong DB
        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            message_type=Message.MessageType.INTERACTIVE_CARD,
            linked_object=appointment,
            content=f"Yêu cầu hẹn gặp cho: {appointment.listing.title}"
        )
        chat.last_message_timestamp = message.created_date
        chat.save()

        # 3. Gửi tin nhắn qua WebSocket bằng Channels Layer
        channel_layer = get_channel_layer()

        serializer_context = {'request': request}

        message_data = MessageSerializer(message).data

        async_to_sync(channel_layer.group_send)(
            f'chat_{chat_pk}',
            {
                'type': 'chat_message',
                'message': message_data
            }
        )

        return Response(message_data, status=status.HTTP_201_CREATED)



class CooperationViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý luồng Hợp tác môi giới.
    - Môi giới (agent) có thể tạo yêu cầu (create).
    - Chủ tin đăng (owner) có thể xem và phản hồi (list, retrieve, respond).
    """
    serializer_class = CooperationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Lọc queryset để người dùng chỉ thấy các hợp tác liên quan đến họ.
        """
        user = self.request.user
        # Người dùng có thể thấy các yêu cầu họ gửi ĐI hoặc nhận ĐẾN
        return Cooperation.objects.filter(
            Q(agent=user) | Q(owner=user)
        ).select_related('listing', 'agent__profile', 'owner__profile')

    def perform_create(self, serializer):
        """
        Ghi đè để tự động điền agent và owner khi tạo yêu cầu.
        """
        listing_id = serializer.validated_data.get('listing_id')
        try:
            listing = Listing.objects.select_related('user').get(id=listing_id)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Tin đăng không tồn tại.")

        agent = self.request.user
        owner = listing.user

        if agent == owner:
            raise serializers.ValidationError("Bạn không thể tự gửi yêu cầu hợp tác cho chính mình.")

        # Lưu yêu cầu với agent và owner đã được xác định
        serializer.save(agent=agent, owner=owner)

    @action(methods=['post'], detail=True, url_path='respond')
    def respond(self, request, pk=None):
        """
        Action để chủ tin đăng phản hồi một yêu cầu (accept/reject).
        URL: /api/cooperations/{id}/respond/
        """
        cooperation = self.get_object()
        action_type = request.data.get('action')  # 'accept' hoặc 'reject'
        reason = request.data.get('reason')  # Lý do (chỉ cần cho 'reject')

        if not action_type in ['accept', 'reject']:
            return Response({'error': 'Hành động không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Chuyển logic này vào service `respond_to_cooperation_request`
        try:
            # Kiểm tra quyền: Chỉ owner mới được respond
            if cooperation.owner != request.user:
                return Response({'error': 'Bạn không có quyền thực hiện hành động này.'},
                                status=status.HTTP_403_FORBIDDEN)

            if action_type == 'accept':
                cooperation.status = Cooperation.Status.ACCEPTED
            elif action_type == 'reject':
                cooperation.status = Cooperation.Status.REJECTED
                cooperation.rejection_reason = reason

            cooperation.save()
            # TODO: Gửi thông báo đến agent

            return Response(self.get_serializer(cooperation).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)