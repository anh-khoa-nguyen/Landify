from rest_framework import parsers, permissions, status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.docs import accounts_docs
from apps.common import perms
from apps.common.services import BusinessLogicError
from apps.common.mixins import DynamicFieldsMixin

from .models import Subscription, User
from . import services as accounts_services # Đổi tên để tránh trùng lặp với module 'accounts'
from .serializers import UserCreateSerializer, UserSerializer, UserUpdateSerializer, UserProfileSerializer, UserProfileDetailSerializer

from apps.listings.serializers import ListingPreviewSerializer
from apps.interactions.serializers import WishlistSerializer
from ..interactions.models import Wishlist
from ..listings.models import Listing


# =================== USER & AUTHENTICATION ==========================

@accounts_docs.auth_viewset_schema
class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet xử lý các hành động liên quan đến xác thực (ví dụ: kết nối Firebase).
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(methods=["post"], detail=False, url_path="connect")
    def connect_firebase_user(self, request):
        """Endpoint xác nhận user đã đăng nhập Firebase."""
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

@accounts_docs.user_viewset_schema
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý người dùng: đăng ký, xem thông tin, cập nhật, theo dõi.
    """
    queryset = User.objects.filter(is_active=True).select_related('profile').prefetch_related('follower_set', 'following_set')

    def get_serializer_class(self):
        if self.action == 'current_user':
            return UserProfileDetailSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update", "complete_profile"]:
            return UserUpdateSerializer
        if self.action == 'retrieve':
            return UserProfileDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in ["retrieve", "list"]:
            return [permissions.AllowAny()]
        if self.action == "disable_account":
            return [perms.IsAdmin()]
        return [permissions.IsAuthenticated()]

    @accounts_docs.current_user_schema
    @action(methods=["get"], detail=False, url_path="current-user")
    def current_user(self, request):
        """Trả về thông tin của người dùng đang đăng nhập."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @accounts_docs.complete_profile_schema
    @action(methods=["patch"], detail=False, url_path="complete-profile")
    def complete_profile(self, request):
        """Người dùng tự cập nhật hồ sơ của mình."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @accounts_docs.change_avatar_schema
    @action(methods=["patch"], detail=False, url_path="change-avatar", parser_classes=[parsers.MultiPartParser])
    def change_avatar(self, request):
        """Người dùng thay đổi ảnh đại diện."""
        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return Response({"error": "Vui lòng cung cấp file ảnh đại diện."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_url = accounts_services.change_user_avatar(user=request.user, avatar_file=avatar_file)
            return Response({"avatar_url": new_url}, status=status.HTTP_200_OK)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @accounts_docs.toggle_follow_schema
    @action(methods=["post"], detail=True, url_path="follow")
    def toggle_follow(self, request, pk=None):
        """Theo dõi hoặc bỏ theo dõi một người dùng khác."""
        user_to_follow = self.get_object()
        try:
            follow_status = accounts_services.toggle_user_follow(follower=request.user, following=user_to_follow)
            if follow_status == "followed":
                return Response({"status": follow_status}, status=status.HTTP_201_CREATED)
            else:
                return Response({"status": follow_status}, status=status.HTTP_204_NO_CONTENT)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=False, url_path="me/wishlist")
    def wishlist(self, request):
        """
        Trả về danh sách các tin đăng trong wishlist của người dùng hiện tại.
        """
        user = request.user
        listing_ids = Wishlist.objects.filter(user=user).values_list('listing_id', flat=True)

        # Truy vấn các tin đăng đó
        queryset = Listing.objects.filter(id__in=listing_ids)

        # Dùng Paginator của ViewSet để phân trang
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Dùng ListingPreviewSerializer để trả về dữ liệu gọn nhẹ
            serializer = ListingPreviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ListingPreviewSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @accounts_docs.disable_account_schema
    @action(methods=["patch"], detail=True, url_path="disable")
    def disable_account(self, request, pk=None):
        """[Admin] Vô hiệu hóa hoặc kích hoạt lại tài khoản người dùng."""
        user_to_toggle = self.get_object()
        try:
            new_status = accounts_services.disable_user_account(admin_user=request.user, user_to_disable=user_to_toggle)
            status_text = "kích hoạt" if new_status else "vô hiệu hóa"
            return Response(
                {"message": f"Đã {status_text} tài khoản '{user_to_toggle.username}'."}, status=status.HTTP_200_OK
            )
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

class SubscriptionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Subscription (Theo dõi)."""

    # Hiển thị thông tin chi tiết của người theo dõi và người được theo dõi
    follower = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))
    following = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))

    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["follower", "following"]