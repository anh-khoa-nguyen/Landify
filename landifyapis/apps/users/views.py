from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from rest_framework import parsers, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common import perms
from apps.common.docs import accounts_docs
from apps.common.mixins import DynamicFieldsMixin
from apps.common.services import BusinessLogicError
from apps.interactions.serializers import WishlistSerializer, CooperationSerializer, ReviewSerializer
from apps.listings.serializers import ListingPreviewSerializer
from apps.moderation.models import Report
from apps.moderation.serializers import ReportSerializer
from apps.social.models import Comment, Post

from ..interactions.models import Cooperation, Review, Wishlist
from ..listings.models import Listing
from . import services as accounts_services
from .models import Subscription, User
from .serializers import (
    UserCreateSerializer,
    UserProfileDescriptionSerializer,
    UserProfileDetailSerializer,
    UserProfileSummarySerializer,
    UserSerializer,
    UserUpdateSerializer,
)

# =================== USER & AUTHENTICATION ==========================


@accounts_docs.auth_viewset_schema
class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet xử lý các hành động liên quan đến xác thực (ví dụ: kết nối Firebase).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    @action(methods=["post"], detail=False, url_path="connect")
    def connect_firebase_user(self, request):
        """Endpoint xác nhận user đã đăng nhập Firebase."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@accounts_docs.user_viewset_schema
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý người dùng: đăng ký, xem thông tin, cập nhật, theo dõi.
    """

    def destroy(self, request, *args, **kwargs):
        target_user = self.get_object()
        acting_user = request.user

        if target_user == acting_user:
            return Response(
                {"error": "Bạn không thể tự xóa tài khoản của chính mình."},
                status=status.HTTP_403_FORBIDDEN
            )

        if target_user.is_superuser:
            return Response(
                {"error": "Không được phép xóa tài khoản Superuser."},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(target_user)

        return Response(status=status.HTTP_204_NO_CONTENT)

    queryset = (
        User.objects.filter(is_active=True)
        .select_related("profile")
        .annotate(
            follower_count=Count("follower_set", distinct=True), following_count=Count("following_set", distinct=True)
        )
    )

    def get_serializer_class(self):
        if self.action in ['current_user', 'retrieve']:
            return UserProfileDetailSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update", "complete_profile"]:
            return UserUpdateSerializer
        if self.action == 'update_description':
            return UserProfileDescriptionSerializer
        if self.action in ['my_wishlist', 'my_listings']:
            return ListingPreviewSerializer
        if self.action == 'reports_received':
            return ReportSerializer
        if self.action in ['cooperations_received', 'cooperations_sent']:
            return CooperationSerializer
        if self.action == 'my_reviews':
            return ReviewSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in ["retrieve", "list"]:
            return [permissions.AllowAny()]
        if self.action in ["listings", "reviews_received", "followers", "following"]:
            return [permissions.AllowAny()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [perms.IsOwnerOrAdmin()]
        if self.action in ["destroy"]:
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

    @action(methods=["patch"], detail=False, url_path="update-description")
    def update_description(self, request):
        """
        Cho phép người dùng đang đăng nhập cập nhật trường 'description' trong hồ sơ của họ.
        """
        user = request.user
        profile = user.profile

        serializer = self.get_serializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Trả về thông tin đầy đủ của User sau khi cập nhật thành công
        return Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_200_OK)

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
        queryset = Listing.objects.filter(id__in=listing_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/listings")
    def my_listings(self, request):
        """
        Trả về danh sách tất cả các tin đăng của người dùng hiện tại.
        """
        user = request.user
        queryset = Listing.objects.filter(user=user).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ListingPreviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ListingPreviewSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/reports-received")
    def reports_received(self, request):
        """
        Trả về danh sách các báo cáo mà người khác đã gửi nhắm vào nội dung của người dùng hiện tại.
        """
        user = request.user
        listing_ct = ContentType.objects.get_for_model(Listing)
        post_ct = ContentType.objects.get_for_model(Post)
        comment_ct = ContentType.objects.get_for_model(Comment)
        user_ct = ContentType.objects.get_for_model(User)

        my_listing_ids = Listing.objects.filter(user=user).values_list('id', flat=True)
        my_post_ids = Post.objects.filter(user=user).values_list('id', flat=True)
        my_comment_ids = Comment.objects.filter(user=user).values_list('id', flat=True)

        listing_reports_q = Q(reported_item_type=listing_ct, reported_item_id__in=my_listing_ids)
        post_reports_q = Q(reported_item_type=post_ct, reported_item_id__in=my_post_ids)
        comment_reports_q = Q(reported_item_type=comment_ct, reported_item_id__in=my_comment_ids)
        user_reports_q = Q(reported_item_type=user_ct, reported_item_id=user.id)

        queryset = Report.objects.filter(
            listing_reports_q | post_reports_q | comment_reports_q | user_reports_q
        ).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/cooperations-sent")
    def cooperations_sent(self, request):
        """
        Trả về danh sách các yêu cầu hợp tác mà người dùng hiện tại đã GỬI ĐI.
        """
        user = request.user
        queryset = Cooperation.objects.filter(agent=user).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="me/cooperations-received")
    def cooperations_received(self, request):
        """
        Trả về danh sách các yêu cầu hợp tác mà người dùng hiện tại đã NHẬN ĐƯỢC.
        """
        user = request.user
        # Thay đổi logic filter: lọc theo trường 'owner' thay vì 'agent'
        queryset = Cooperation.objects.filter(owner=user).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            # get_serializer() sẽ tự động trả về CooperationSerializer như đã định nghĩa
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

    @action(methods=["get"], detail=True, url_path="listings", permission_classes=[permissions.AllowAny])
    def listings(self, request, pk=None):
        """
        Trả về danh sách các tin đăng đang hoạt động của một người dùng cụ thể.
        """
        user = self.get_object()  # self.get_object() sẽ lấy user dựa trên 'pk' từ URL

        # Lọc các tin đăng của user đó
        queryset = Listing.objects.filter(user=user, active=True, status=Listing.Status.AVAILABLE).order_by(
            '-created_date')

        # Áp dụng phân trang
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Sử dụng ListingPreviewSerializer để trả về dữ liệu gọn nhẹ
            serializer = ListingPreviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ListingPreviewSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=True, url_path="reviews-received", permission_classes=[permissions.AllowAny])
    def reviews_received(self, request, pk=None):
        """
        Trả về danh sách các đánh giá mà các bất động sản của người dùng này đã nhận.
        """
        user = self.get_object()

        # Truy vấn phức tạp: Lấy các Review mà 'property__owner' là user này
        queryset = Review.objects.filter(property__owner=user, active=True).select_related(
            'user__profile',  # Tối ưu để lấy thông tin người đánh giá
            'property'
        ).order_by('-created_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            # Sử dụng ReviewSerializer để trả về dữ liệu chi tiết
            serializer = ReviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ReviewSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=True, url_path="followers", permission_classes=[permissions.AllowAny])
    def followers(self, request, pk=None):
        """
        Trả về danh sách những người đang theo dõi user này.
        """
        user = self.get_object()
        # Truy vấn ngược từ Subscription: lấy tất cả subscription mà 'following' là user hiện tại.
        # Sau đó select_related 'follower' để lấy thông tin người theo dõi.
        subscriptions = user.follower_set.select_related("follower__profile").order_by("-created_date")

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            # Chúng ta cần một serializer để chỉ lấy thông tin user từ subscription
            # Cách đơn giản nhất là dùng một list comprehension hoặc một serializer tùy chỉnh.
            # Ở đây tôi dùng cách thủ công để bạn dễ hình dung, bạn có thể tạo serializer riêng nếu muốn.
            follower_users = [sub.follower for sub in page]
            # Tái sử dụng UserSerializer để hiển thị thông tin người dùng
            serializer = UserSerializer(follower_users, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        follower_users = [sub.follower for sub in subscriptions]
        serializer = UserSerializer(follower_users, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=["get"], detail=True, url_path="following", permission_classes=[permissions.AllowAny])
    def following(self, request, pk=None):
        """
        Trả về danh sách những người mà user này đang theo dõi.
        """
        user = self.get_object()
        # Truy vấn ngược từ Subscription: lấy tất cả subscription mà 'follower' là user hiện tại.
        subscriptions = user.following_set.select_related("following__profile").order_by("-created_date")

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            following_users = [sub.following for sub in page]
            serializer = UserSerializer(following_users, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        following_users = [sub.following for sub in subscriptions]
        serializer = UserSerializer(following_users, many=True, context={'request': request})
        return Response(serializer.data)
