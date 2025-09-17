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
from .option_serializers import FilterableFeatureSerializer # Import từ vị trí mới

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
            'listing_type',
            'unit_price',
            'vip_status__vip_type',  # Tối ưu cho việc lấy tag VIP
        )
        .prefetch_related(
            'feature_values__feature',
            'property__media',
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
        Ghi đè logic tạo mới để gọi đến service function.
        """
        # 1. Khởi tạo serializer để validate dữ liệu đầu vào
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Lấy dữ liệu đã được validate
        validated_data = serializer.validated_data

        # 3. Tách các thông tin cần thiết để gọi service
        # Nhờ PrimaryKeyRelatedField, 'listing_category' giờ là một object đầy đủ
        category = validated_data.pop('listing_category')

        # 4. Gọi đến service để thực hiện toàn bộ logic nghiệp vụ phức tạp
        try:
            new_listing = listing_services.create_full_listing(
                user=request.user,
                listing_type=category.listing_type,
                property_type=category.property_type,
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
    def wishlist(self, request, pk=None):
        """
        Thêm/Xóa (toggle) tin đăng này vào danh sách yêu thích của người dùng.
        """
        # 1. Lấy đối tượng Listing dựa trên public_id từ URL
        # Lưu ý: Vì action này nằm trong UserViewSet, chúng ta cần get_object_or_404 cho Listing
        listing = get_object_from_public_id_or_404(Listing.objects, pk)
        user = request.user

        # 2. Gọi service để xử lý toàn bộ logic nghiệp vụ
        try:
            status, wishlist_item = interactions_services.toggle_wishlist_item(
                user=user,
                listing=listing
            )

            # 3. Trả về response dựa trên kết quả từ service
            if status == "added":
                serializer = WishlistSerializer(wishlist_item, context={'request': request})
                return Response({
                    "status": "added",
                    "message": "Đã thêm vào danh sách yêu thích.",
                    "wishlist_item": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:  # status == "removed"
                return Response({
                    "status": "removed",
                    "message": "Đã xóa khỏi danh sách yêu thích."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            # Bắt các lỗi không lường trước
            return Response(
                {"error": f"Đã có lỗi xảy ra: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            return Response(
                {"error": f"Đã có lỗi xảy ra: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=["get"], detail=False, url_path="potential")
    def potential(self, request):
        """
        Gợi ý các tin đăng tiềm năng nhất dựa trên vị trí và nhiều yếu tố khác.
        Yêu cầu các tham số query: 'lat' (vĩ độ) và 'lng' (kinh độ).
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
        potential_listings_qs = listing_services.find_potential_listings(latitude=lat, longitude=lng)

        # Phân trang và trả về kết quả
        page = self.paginate_queryset(potential_listings_qs)
        if page is not None:
            # Dùng ListingPreviewSerializer, nó sẽ tự động lấy trường 'potential_score'
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(potential_listings_qs, many=True, context={'request': request})
        return Response(serializer.data)

# ==============================================================================
# HELPER & OPTION VIEWS
# ==============================================================================
# Các API View này cung cấp dữ liệu cần thiết cho frontend để xây dựng
# giao diện người dùng, chẳng hạn như các tùy chọn cho bộ lọc và form tạo tin.
class ListingFilterOptionsView(APIView):
    """
    Cung cấp TOÀN BỘ dữ liệu cần thiết để xây dựng giao diện BỘ LỌC NÂNG CAO.
    API này sử dụng một trường feature duy nhất (`applicable_features`) cho cả
    form đăng tin và bộ lọc.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        # 1. Lấy các bộ lọc chung từ CSDL
        cities = City.objects.filter(is_popular=True).order_by('name')
        listing_types = ListingType.objects.filter(active=True)

        # 2. Lấy tất cả các category và prefetch các feature liên quan của chúng
        categories = ListingCategory.objects.filter(active=True).prefetch_related('applicable_features')

        # 3. Xây dựng cấu trúc dữ liệu cho các bộ lọc đặc thù
        #    Đây là phần logic chính, nhóm các feature theo ID của category
        specific_filters_by_category = {}
        for category in categories:
            # Key là ID của category, value là danh sách các feature đã được serialize
            serialized_features = FilterableFeatureSerializer(category.applicable_features, many=True).data
            specific_filters_by_category[category.id] = serialized_features

        # 4. Xây dựng các lựa chọn tĩnh cho khoảng giá
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

        # 5. Gom tất cả dữ liệu vào response cuối cùng
        data = {
            # --- CÁC BỘ LỌC CHUNG ---
            'cities': [{'code': c.code, 'name': c.name} for c in cities],
            'listing_types': [{'code': lt.code, 'name': lt.name} for lt in listing_types],
            'price_ranges': {
                'RENT': price_ranges_rent,
                'BUY_SELL': price_ranges_sell,
            },

            # --- CÁC BỘ LỌC ĐẶC THÙ ---
            'specific_filters_by_category': specific_filters
        }
        return Response(data)

class ListingCreationOptionsView(APIView):
    """
    Cung cấp tất cả các dữ liệu lựa chọn cần thiết
    cho việc tạo một tin đăng mới.
    """
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đăng nhập mới được tạo tin

    def get(self, request, format=None):
        directions = Direction.objects.filter(active=True)
        legal_statuses = LegalStatus.objects.filter(active=True)
        # unit_prices = UnitPrice.objects.all()  # Giả sử UnitPrice không có cờ active
        # property_features = PropertyFeature.objects.filter(active=True).order_by('category', 'name')
        vip_types = VipType.objects.filter(active=True).order_by('-sort_priority')

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

        # Serialize dữ liệu
        data = {
            'grouped_categories': list(grouped_categories.values()),
            'directions': DirectionOptionSerializer(directions, many=True).data,
            'legal_statuses': LegalStatusOptionSerializer(legal_statuses, many=True).data,
            'vip_types': VipTypeOptionSerializer(vip_types, many=True).data,
            'promotions': UserPromotionOptionSerializer(valid_promotions, many=True).data,
        }

        return Response(data, status=status.HTTP_200_OK)
