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
from ..interactions.models import Wishlist, Cooperation, Review
from ..listings.models import Listing

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from apps.social.models import Post, Comment
from apps.moderation.models import Report
from apps.moderation.serializers import ReportSerializer

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
    def my_wishlist(self, request):
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

    @action(methods=["get"], detail=False, url_path="me/listings")
    def my_listings(self, request):
        """
        Trả về danh sách tất cả các tin đăng của người dùng hiện tại,
        bao gồm cả tin đã ẩn hoặc có trạng thái khác AVAILABLE.
        """
        user = request.user

        # 1. Truy vấn tất cả tin đăng của người dùng này, sắp xếp theo ngày tạo mới nhất
        #    Quan trọng: Chúng ta không lọc theo active=True hay status='AVAILABLE'
        #    vì người dùng cần xem tất cả tin đăng của họ để quản lý.
        queryset = Listing.objects.filter(user=user).order_by('-created_date')

        # 2. Phân trang kết quả
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Dùng ListingPreviewSerializer để trả về dữ liệu gọn nhẹ, phù hợp cho danh sách
            serializer = ListingPreviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        # 3. Serialize và trả về nếu không phân trang
        serializer = ListingPreviewSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/reports-received")
    def reports_received(self, request):
        """
        Trả về danh sách các báo cáo mà người khác đã gửi nhắm vào
        nội dung (tin đăng, bài viết, bình luận) của người dùng hiện tại.
        """
        user = request.user

        # 1. Lấy ContentType cho các model có thể bị báo cáo
        listing_ct = ContentType.objects.get_for_model(Listing)
        post_ct = ContentType.objects.get_for_model(Post)
        comment_ct = ContentType.objects.get_for_model(Comment)
        user_ct = ContentType.objects.get_for_model(User)

        # 2. Tìm ID của tất cả nội dung thuộc sở hữu của người dùng
        my_listing_ids = Listing.objects.filter(user=user).values_list('id', flat=True)
        my_post_ids = Post.objects.filter(user=user).values_list('id', flat=True)
        my_comment_ids = Comment.objects.filter(user=user).values_list('id', flat=True)

        # 3. Xây dựng các điều kiện truy vấn (Q objects)
        # Báo cáo nhắm vào tin đăng của tôi
        listing_reports_q = Q(reported_item_type=listing_ct, reported_item_id__in=my_listing_ids)
        # Báo cáo nhắm vào bài viết của tôi
        post_reports_q = Q(reported_item_type=post_ct, reported_item_id__in=my_post_ids)
        # Báo cáo nhắm vào bình luận của tôi
        comment_reports_q = Q(reported_item_type=comment_ct, reported_item_id__in=my_comment_ids)
        # Báo cáo nhắm vào chính tài khoản của tôi
        user_reports_q = Q(reported_item_type=user_ct, reported_item_id=user.id)

        # 4. Kết hợp các điều kiện và truy vấn
        queryset = Report.objects.filter(
            listing_reports_q | post_reports_q | comment_reports_q | user_reports_q
        ).order_by('-created_date')

        # 5. Phân trang và trả về kết quả
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReportSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ReportSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/cooperations-received")
    def cooperations_received(self, request):
        """
        Trả về danh sách các yêu cầu hợp tác mà người dùng hiện tại đã NHẬN ĐƯỢỢC
        (với vai trò là chủ tin đăng).
        """
        user = request.user
        # Lọc các Cooperation mà người dùng hiện tại là 'owner'
        queryset = Cooperation.objects.filter(owner=user).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/cooperations-sent")
    def cooperations_sent(self, request):
        """
        Trả về danh sách các yêu cầu hợp tác mà người dùng hiện tại đã GỬI ĐI
        (với vai trò là môi giới).
        """
        user = request.user
        # Lọc các Cooperation mà người dùng hiện tại là 'agent'
        queryset = Cooperation.objects.filter(agent=user).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/reviews")
    def my_reviews(self, request):
        """
        Trả về danh sách tất cả các đánh giá (review) mà người dùng hiện tại đã gửi.
        """
        user = request.user

        # Lọc các Review mà người dùng hiện tại là 'user'
        # Dùng select_related để tối ưu, lấy sẵn thông tin của Bất động sản liên quan
        queryset = Review.objects.filter(user=user).select_related(
            'property__property_type',
            'property__location'
        ).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
