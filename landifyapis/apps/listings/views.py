# landifys/views/listings.py

# Django Core
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction  # Cần cho transaction.atomic
from django.db.models import Avg, Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404

# REST Framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, parsers, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

# Doc
from apps.common.docs import listings_docs, media_docs

# Modules
from apps.common import perms, tasks
from .models import Property, Listing, VipType, ListingType, UserPromotion
from .filters import ListingFilter
from . import services as listing_services
from .serializers import ListingPreviewSerializer, ListingDetailSerializer, ListingCreateSerializer

from apps.moderation.serializers import ProtestSerializer
from apps.common.utils import hashids
from apps.common.services import BusinessLogicError
from apps.common.utils.hashids import get_object_from_public_id_or_404

#---------CREATE LISTING OPTION---------
from apps.properties.models import PropertyType, Direction, LegalStatus, PropertyFeature
from .models import UnitPrice
from .option_serializers import (
    PropertyTypeOptionSerializer,
    DirectionOptionSerializer,
    LegalStatusOptionSerializer,
    UnitPriceOptionSerializer,
    VipTypeOptionSerializer,
    PropertyFeatureSerializer,
    UserPromotionOptionSerializer, ListingTypeOptionSerializer,
)
from django.utils import timezone
#------------SEARCH LISTING------------
from vi_address.models import City

from ..interactions.models import Wishlist
from ..interactions.serializers import WishlistSerializer


@listings_docs.listing_viewset_schema
class ListingViewSet(viewsets.ModelViewSet):
    """ViewSet để quản lý Tin đăng."""
    filter_backends = [DjangoFilterBackend] # Kích hoạt backend lọc
    filterset_class = ListingFilter
    lookup_field = "public_id"

    def get_permissions(self):
        # Cho phép bất kỳ ai cũng có thể xem danh sách và xem chi tiết
        if self.action in ['list', 'retrieve', 'search']:  # Thêm 'search' nếu bạn có action này
            return [permissions.AllowAny()]

        # Đối với tất cả các action khác (create, update, destroy, wishlist, protest...),
        # yêu cầu người dùng phải đăng nhập.
        return [permissions.IsAuthenticated()]

    queryset = (
        Listing.objects.filter(active=True, status=Listing.Status.AVAILABLE)
        .select_related(
            'user__profile',  # Lấy User và UserProfile liên quan trong 1 query
            'property__location__ward__parent_code__parent_code',  # Lấy Property, Location, Ward, District, City
            'listing_type',
            'unit_price',
            'buysell_detail',  # Lấy các detail model (OneToOne)
            'rental_detail',
            'project_detail',
        )
        .prefetch_related(
            'feature_values__feature',  # Lấy tất cả feature_values và feature liên quan
            'property__media',  # Lấy tất cả media của property
        )
    )

    lookup_field = "public_id"

    def get_serializer_class(self):
        if self.action == "create":
            return ListingCreateSerializer

        # === THAY ĐỔI Ở ĐÂY ===
        # Nếu action là 'list' (lấy danh sách), dùng PreviewSerializer
        if self.action == 'list' or self.action == 'search':
            return ListingPreviewSerializer

        # Mặc định (cho 'retrieve' - lấy chi tiết), dùng DetailSerializer
        return ListingDetailSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_object(self):
        public_id = self.kwargs[self.lookup_field]
        obj = get_object_from_public_id_or_404(self.get_queryset(), public_id)
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        """
        Ghi đè logic tạo mới để có thể sử dụng serializer khác cho response.
        - Dùng ListingCreateSerializer để validate dữ liệu đầu vào.
        - Dùng ListingDetailSerializer để serialize dữ liệu đầu ra.
        """
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        # 2. Gọi service để thực hiện việc lưu vào database
        #    Hàm này sẽ trả về instance Listing vừa được tạo.
        listing_instance = listing_services.create_full_listing(
            user=request.user,
            validated_data=create_serializer.validated_data
        )

        # 3. Lấy serializer dùng để ĐỌC (tạo response trả về)
        #    Chúng ta khởi tạo nó một cách tường minh.
        response_serializer = ListingDetailSerializer(listing_instance, context=self.get_serializer_context())

        # 4. Tạo và trả về response 201 Created với dữ liệu đầy đủ
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @listings_docs.update_features_schema
    @action(methods=["patch"], detail=True, url_path="update-features")
    def update_features(self, request, public_id=None):
        listing = self.get_object()

        features_data = request.data.get("features")
        if features_data is None:
            return Response({"error": "Trường 'features' là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            listing_services.update_listing_features(listing=listing, features_data=features_data)
            serializer = self.get_serializer(listing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @listings_docs.protest_listing_schema
    @action(methods=["post"], detail=True)
    def protest(self, request, public_id=None): # <<< Đổi tên tham số cho nhất quán
        """Người dùng kháng nghị khi tin đăng của họ bị từ chối/gắn cờ."""
        listing = self.get_object()
        serializer = ProtestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            protest = listing_services.create_protest_for_listing(
                listing=listing, protester=request.user, serializer=serializer
            )
            return Response(ProtestSerializer(protest).data, status=status.HTTP_201_CREATED)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="wishlist")
    def wishlist(self, request, public_id=None):
        """
        Thêm/Xóa (toggle) tin đăng này vào danh sách yêu thích của người dùng.
        """
        # 1. Lấy đối tượng Listing dựa trên public_id từ URL
        listing = self.get_object()
        user = request.user

        # 2. Thực hiện logic toggle
        try:
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=user,
                listing=listing
            )

            if created:
                # Nếu vừa được TẠO MỚI (thêm vào)
                serializer = WishlistSerializer(wishlist_item, context={'request': request})
                return Response({
                    "status": "added",
                    "message": "Đã thêm vào danh sách yêu thích.",
                    "wishlist_item": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                # Nếu đã TỒN TẠI -> XÓA ĐI
                wishlist_item.delete()
                return Response({
                    "status": "removed",
                    "message": "Đã xóa khỏi danh sách yêu thích."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Đã có lỗi xảy ra: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ListingFilterOptionsView(APIView):
    """
    Cung cấp các dữ liệu cần thiết để xây dựng giao diện bộ lọc.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        # Lấy các thành phố phổ biến
        cities = City.objects.filter(is_popular=True).order_by('name') # Giả sử có cờ is_popular
        # Lấy tất cả các loại BĐS
        property_types = PropertyType.objects.filter(active=True)

        data = {
            'cities': [{'code': c.code, 'name': c.name} for c in cities],
            'property_types': [{'code': pt.code, 'name': pt.name} for pt in property_types],
            'price_ranges': [
                {'label': 'Dưới 1 tỷ', 'min': 0, 'max': 1000000000},
                {'label': '1 - 3 tỷ', 'min': 1000000000, 'max': 3000000000},
                # ... các khoảng giá khác ...
            ],
            # ... các lựa chọn khác như hướng nhà, số phòng ngủ ...
        }
        return Response(data)

class ListingCreationOptionsView(APIView):
    """
    Cung cấp tất cả các dữ liệu lựa chọn cần thiết
    cho việc tạo một tin đăng mới.
    """
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đăng nhập mới được tạo tin

    def get(self, request, format=None):
        # Truy vấn tất cả các lựa chọn từ database
        property_types = PropertyType.objects.filter(active=True)
        listing_types = ListingType.objects.filter(active=True)
        directions = Direction.objects.filter(active=True)
        legal_statuses = LegalStatus.objects.filter(active=True)
        unit_prices = UnitPrice.objects.all()  # Giả sử UnitPrice không có cờ active
        property_features = PropertyFeature.objects.filter(active=True).order_by('category', 'name')
        vip_types = VipType.objects.filter(active=True).order_by('-sort_priority')

        valid_promotions = UserPromotion.objects.filter(
            user=request.user,
            status=UserPromotion.Status.AVAILABLE,
            expiry_date__gte=timezone.now()
        )

        # Serialize dữ liệu
        data = {
            'property_types': PropertyTypeOptionSerializer(property_types, many=True).data,
            'listing_types': ListingTypeOptionSerializer(listing_types, many=True).data,
            'directions': DirectionOptionSerializer(directions, many=True).data,
            'legal_statuses': LegalStatusOptionSerializer(legal_statuses, many=True).data,
            'unit_prices': UnitPriceOptionSerializer(unit_prices, many=True).data,
            'property_features': PropertyFeatureSerializer(property_features, many=True,
                                                           context={'request': request}).data,
            'vip_types': VipTypeOptionSerializer(vip_types, many=True).data,
            'promotions': UserPromotionOptionSerializer(valid_promotions, many=True).data,
        }

        return Response(data, status=status.HTTP_200_OK)
