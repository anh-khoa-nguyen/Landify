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
from .models import Property, Listing, VipType, ListingType, UserPromotion, ListingCategory
from .filters import ListingFilter
from . import services as listing_services
from .serializers import ListingPreviewSerializer, ListingDetailSerializer, ListingCreateSerializer

from apps.moderation.serializers import ProtestSerializer
from apps.common.utils import hashids
from apps.common.services import BusinessLogicError
from apps.common.utils.hashids import get_object_from_public_id_or_404
from apps.interactions import services as interactions_services # Import service mới

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
    UserPromotionOptionSerializer, ListingTypeOptionSerializer, ListingCategoryOptionSerializer,
)
from django.utils import timezone
#------------SEARCH LISTING------------
from vi_address.models import City

from ..interactions.models import Wishlist
from ..interactions.serializers import WishlistSerializer

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

# ==============================================================================
# CORE LISTING VIEWSET
# ==============================================================================
# ViewSet chính quản lý tất cả các hoạt động CRUD và các action tùy chỉnh
# liên quan đến Tin đăng (Listing).

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
            'user__profile',
            'property__location__ward__parent_code__parent_code',
            # Sửa đường dẫn truy vấn để đi qua listing_category
            'listing_category__listing_type',
            'listing_category__property_type',
            'unit_price',
            'vip_status__vip_type',
        )
        .annotate(
            user_follower_count=Count('user__follower_set', distinct=True),
            user_following_count=Count('user__following_set', distinct=True),
        )
        .prefetch_related(
            'feature_values__feature',
            'property__media',
        )
        .order_by('-created_date')
    )

    lookup_field = "public_id"

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        # 1. Tối ưu hóa: Lấy tất cả các feature codes và types cần thiết trong 1 query
        feature_params = {}
        for key in self.request.query_params:
            if key.startswith('features__'):
                parts = key.split('__')
                if len(parts) == 3:
                    feature_params[parts[1]] = None  # Chỉ cần lấy code

        if not feature_params:
            return queryset  # Trả về sớm nếu không có filter feature nào

        features_map = {
            f.code: f.feature_type
            for f in PropertyFeature.objects.filter(code__in=feature_params.keys())
        }

        # 2. Xử lý các bộ lọc feature động với kiểu dữ liệu chính xác
        for key, value in self.request.query_params.items():
            if key.startswith('features__'):
                parts = key.split('__')
                if len(parts) == 3:
                    feature_code = parts[1]
                    lookup_expr = parts[2]

                    feature_type = features_map.get(feature_code)
                    if not feature_type:
                        continue  # Bỏ qua nếu feature_code không hợp lệ

                    # 3. Chuyển đổi kiểu dữ liệu thông minh
                    processed_value = value
                    if feature_type == PropertyFeature.FeatureType.BOOLEAN:
                        if value.lower() == 'true':
                            processed_value = True
                        elif value.lower() == 'false':
                            processed_value = False
                    elif feature_type == PropertyFeature.FeatureType.FLOAT:
                        try:
                            processed_value = float(value)
                        except (ValueError, TypeError):
                            return queryset.none()
                    # Các kiểu khác (TEXT, DIRECTION...) giữ nguyên là chuỗi/số từ URL

                    q_object = Q(
                        feature_values__feature__code=feature_code,
                        **{f'feature_values__value__{lookup_expr}': processed_value}
                    )
                    queryset = queryset.filter(q_object)

        return queryset.distinct()

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
        Ghi đè logic tạo mới để gọi đến service function.
        """
        # 1. Khởi tạo serializer để validate dữ liệu đầu vào
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Lấy dữ liệu đã được validate
        validated_data = serializer.validated_data

        # 4. Gọi đến service để thực hiện toàn bộ logic nghiệp vụ phức tạp
        try:
            new_listing = listing_services.create_full_listing(
                user=request.user,
                validated_data=validated_data
            )
        except BusinessLogicError as e:
            # Bắt các lỗi nghiệp vụ từ service và trả về lỗi 400
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 5. Serialize kết quả trả về bằng serializer chi tiết
        response_serializer = ListingDetailSerializer(new_listing, context=self.get_serializer_context())

        # 6. Trả về response thành công
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

    # @listings_docs.protest_listing_schema
    # @action(methods=["post"], detail=True)
    # def protest(self, request, public_id=None): # <<< Đổi tên tham số cho nhất quán
    #     """Người dùng kháng nghị khi tin đăng của họ bị từ chối/gắn cờ."""
    #     listing = self.get_object()
    #     serializer = ProtestSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     try:
    #         protest = listing_services.create_protest_for_listing(
    #             listing=listing, protester=request.user, serializer=serializer
    #         )
    #         return Response(ProtestSerializer(protest).data, status=status.HTTP_201_CREATED)
    #     except BusinessLogicError as e:
    #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="wishlist")
    def wishlist(self, request, public_id=None):
        """
        Thêm/Xóa (toggle) tin đăng này vào danh sách yêu thích của người dùng.
        """
        listing = get_object_from_public_id_or_404(Listing.objects, public_id)
        user = request.user

        try:
            # Đổi tên biến cục bộ để tránh che mất module `status`
            toggle_status, wishlist_item = interactions_services.toggle_wishlist_item(
                user=user,
                listing=listing
            )

            if toggle_status == "added":
                serializer = WishlistSerializer(wishlist_item, context={'request': request})
                return Response({
                    "status": "added",
                    "message": "Đã thêm vào danh sách yêu thích.",
                    "wishlist_item": serializer.data
                    # Sử dụng module `status` của DRF một cách tường minh
                }, status=status.HTTP_201_CREATED)
            else:  # toggle_status == "removed"
                return Response({
                    "status": "removed",
                    "message": "Đã xóa khỏi danh sách yêu thích."
                    # Sử dụng module `status` của DRF một cách tường minh
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Đã có lỗi xảy ra: {str(e)}"},
                # Sử dụng module `status` của DRF một cách tường minh
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=["get"], detail=False, url_path="potential")
    def potential(self, request):
        """
        Gợi ý các tin đăng tiềm năng nhất, có thể có hoặc không có bộ lọc.
        - Trang chủ sẽ gọi: /api/listings/potential/?lat=...&lng=...
        - Trang tìm kiếm sẽ gọi: /api/listings/potential/?lat=...&lng=...&beds=3&min_price=...
        """
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
        except (TypeError, ValueError):
            return Response(
                {"error": "Vui lòng cung cấp vĩ độ ('lat') và kinh độ ('lng') hợp lệ."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Gọi service để lấy queryset đã được tính điểm và sắp xếp
        filters = request.query_params.dict()

        potential_listings_qs = listing_services.find_potential_listings(
            latitude=lat,
            longitude=lng,
            filters=filters
        )

        page = self.paginate_queryset(potential_listings_qs)
        if page is not None:
            # Dùng ListingPreviewSerializer, nó sẽ tự động lấy các trường đã annotate
            serializer = ListingPreviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ListingPreviewSerializer(potential_listings_qs, many=True, context={'request': request})
        return Response(serializer.data)

# ==============================================================================
# HELPER & OPTION VIEWS
# ==============================================================================
# Các API View này cung cấp dữ liệu cần thiết cho frontend để xây dựng
# giao diện người dùng, chẳng hạn như các tùy chọn cho bộ lọc và form tạo tin.

class ListingOptionsView(APIView):
    """
    API DUY NHẤT cung cấp TẤT CẢ các dữ liệu lựa chọn.
    Sử dụng tham số query `?context=` để tùy chỉnh response:
    - `?context=create`: Dành cho form Đăng tin.
    - `?context=filter`: Dành cho Bộ lọc Tìm kiếm.
    - (Mặc định): Trả về tất cả.
    """
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đăng nhập mới được tạo tin

    def get(self, request, format=None):
        directions = Direction.objects.filter(active=True)
        legal_statuses = LegalStatus.objects.filter(active=True)
        # unit_prices = UnitPrice.objects.all()  # Giả sử UnitPrice không có cờ active
        # property_features = PropertyFeature.objects.filter(active=True).order_by('category', 'name')
        vip_types = VipType.objects.filter(active=True).order_by('-sort_priority')
        cities = City.objects.all().order_by('name')
        listing_types = ListingType.objects.filter(active=True)

        valid_promotions = UserPromotion.objects.filter(
            user=request.user,
            status=UserPromotion.Status.AVAILABLE,
            expiry_date__gte=timezone.now()
        )
        categories = ListingCategory.objects.select_related(
            'listing_type', 'property_type'
        ).prefetch_related(
            'applicable_features',
            'listing_type__applicable_unit_prices' # Prefetch cả unit_prices
        ).filter(active=True)

        grouped_categories = {}
        for category in categories:
            lt = category.listing_type
            if lt.code not in grouped_categories:
                grouped_categories[lt.code] = {
                    'listing_type_name': lt.name,
                    'listing_type_code': lt.code,
                    'categories': []
                }
            grouped_categories[lt.code]['categories'].append(
                ListingCategoryOptionSerializer(category).data
            )

        price_ranges_rent = [
            {'min': 0, 'max': 5000000, 'label': 'Dưới 5 triệu'},
            {'min': 5000000, 'max': 10000000, 'label': '5 - 10 triệu'},
            {'min': 10000000, 'max': 20000000, 'label': '10 - 20 triệu'},
            {'min': 20000000, 'max': 0, 'label': 'Trên 20 triệu'},
        ]
        price_ranges_sell = [
            {'min': 0, 'max': 1000000000, 'label': 'Dưới 1 tỷ'},
            {'min': 1000000000, 'max': 3000000000, 'label': '1 - 3 tỷ'},
            {'min': 3000000000, 'max': 5000000000, 'label': '3 - 5 tỷ'},
            {'min': 5000000000, 'max': 0, 'label': 'Trên 5 tỷ'},
        ]

        # Serialize dữ liệu
        all_data = {
            'grouped_categories': list(grouped_categories.values()),
            'directions': DirectionOptionSerializer(directions, many=True).data,
            'legal_statuses': LegalStatusOptionSerializer(legal_statuses, many=True).data,
            'vip_types': VipTypeOptionSerializer(vip_types, many=True).data,
            'promotions': UserPromotionOptionSerializer(valid_promotions, many=True).data,
            'cities': [{'code': c.code, 'name': c.name} for c in cities],
            'listing_types': [{'code': lt.code, 'name': lt.name} for lt in listing_types],
            'price_ranges': {
                'RENT': price_ranges_rent,
                'BUY_SELL': price_ranges_sell,
            },
        }

        context = request.query_params.get('context')

        if context == 'create':
            # Nếu là context "tạo tin", loại bỏ các trường của "filter"
            keys_to_remove = ['cities', 'listing_types', 'price_ranges']
            for key in keys_to_remove:
                all_data.pop(key, None)

        elif context == 'filter':
            # Nếu là context "lọc tin", loại bỏ các trường của "create"
            keys_to_remove = ['vip_types', 'promotions']
            for key in keys_to_remove:
                all_data.pop(key, None)

        return Response(all_data, status=status.HTTP_200_OK)
