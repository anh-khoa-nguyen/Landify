# apps/properties/serializers.py
from datetime import date

from django.utils import timezone
from rest_framework import serializers
from vi_address.models import Ward

from apps.common.mixins import DynamicFieldsMixin
from apps.common.frontend_maps import feature_maps
from apps.users.serializers import UserSerializer
from apps.properties.serializers import PropertySerializer, PropertyFeatureSerializer, LocationSerializer
from apps.common.utils.hashids import hashids
from apps.properties.models import Property, PropertyType, PropertyFeature, Direction, LegalStatus

from .models import ListingPropertyFeatureValue, Listing, ListingType, UnitPrice, VipType, UserPromotion, \
    ListingCategory
from .models import BuySellDetail, ProjectDetail, RentalDetail
from . import services as listings_services

# ==============================================================================
# DETAIL SERIALIZERS
# ==============================================================================

class BuySellDetailSerializer(serializers.ModelSerializer):
    """
    Serializer cho các thông tin chi tiết của một tin đăng Mua/Bán.
    Chủ yếu được sử dụng để ghi dữ liệu lồng nhau trong ListingCreateSerializer
    và đọc dữ liệu trong ListingSerializer.
    """

    class Meta:
        model = BuySellDetail
        # Bao gồm tất cả các trường mà người dùng có thể nhập
        fields = [
            "condition_status",
            "is_mortgaged",
        ]

class RentalDetailSerializer(serializers.ModelSerializer):
    """
    Serializer cho các thông tin chi tiết của một tin đăng Cho Thuê.
    """

    class Meta:
        model = RentalDetail
        # Bao gồm tất cả các trường mà người dùng có thể nhập
        fields = [
            "deposit_amount",
            "min_lease_duration",
            "allow_pets",
            "allow_smoking",
            "max_occupants",
            "is_electricity_included",
            "is_water_included",
            "is_internet_included",
            "is_management_fee_included",
            "available_from_date",
        ]

class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    Serializer cho các thông tin chi tiết của một tin đăng Dự án.
    """

    class Meta:
        model = ProjectDetail
        # Bao gồm tất cả các trường mà người dùng có thể nhập
        fields = [
            "developer",
            "total_area",
            "building_density",
            "scale_description",
            "total_units",
            "product_types",
            "unit_area_range",
            "ownership_form",
            "launch_date",
            "handover_date",
        ]
# ==============================================================================
# LOCATION, PROPERTY, LISTING SERIALIZERS
# ==============================================================================

class ListingPropertyFeatureValueSerializer(serializers.ModelSerializer):
    """Serializer cho bảng trung gian, lồng thông tin chi tiết của Feature."""

    feature = PropertyFeatureSerializer(read_only=True)

    class Meta:
        model = ListingPropertyFeatureValue
        fields = ["feature", "value"]

class ListingPreviewSerializer(serializers.ModelSerializer):
    """
    Serializer chuyên dụng để hiển thị tin đăng ở dạng xem trước (preview).
    Nó làm phẳng cấu trúc dữ liệu và chỉ trả về các thông tin cần thiết cho UI.
    """
    public_id = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    display_price = serializers.CharField(read_only=True)
    price_value = serializers.FloatField(read_only=True)
    unit_price_code = serializers.CharField(source="unit_price.code", read_only=True, allow_null=True)
    area = serializers.SerializerMethodField()
    beds = serializers.SerializerMethodField()
    baths = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    agent_name = serializers.CharField(source="user.get_full_name", read_only=True)
    agent_avatar = serializers.URLField(source="user.profile.avatar.url", read_only=True, allow_null=True)
    agent_phone = serializers.CharField(source="user.phone_number", read_only=True)
    owner_id = serializers.IntegerField(source='user.id', read_only=True)
    image_urls = serializers.SerializerMethodField()
    total_image_count = serializers.SerializerMethodField()
    total_video_count = serializers.SerializerMethodField()

    is_in_wishlist = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    potential_score = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Listing
        fields = [
            'public_id',
            'title',
            'tag',
            'display_price',
            'price_value',
            'unit_price_code',
            'area',
            'beds',
            'baths',
            'address',
            'agent_name',
            'agent_avatar',
            'agent_phone',
            'owner_id',
            'image_urls',
            'total_image_count',
            'total_video_count',
            'created_date',
            'is_in_wishlist',
            'distance_km',
            'potential_score',
        ]

    def get_public_id(self, obj: Listing) -> str:
        return hashids.encode(obj.id)

    def get_tag(self, obj: Listing) -> str | None:
        # TODO: Implement logic to get VIP status tag
        # Ví dụ:
        # vip_status = obj.vip_status.filter(is_active=True).order_by('-vip_type__sort_priority').first()
        # return vip_status.vip_type.name if vip_status else "Tin thường"
        return "VIP Kim Cương"  # Placeholder

    def get_area(self, obj: Listing) -> str:
        if obj.property and obj.property.area:
            return f"{obj.property.area} m²"
        return ""

    def get_address(self, obj: Listing) -> str:
        location = obj.property.location
        if location:
            district_name = getattr(location.district, 'name', None)
            city_name = getattr(location.city, 'name', None)

            # Xây dựng danh sách các phần của địa chỉ
            parts = []
            if district_name:
                parts.append(district_name)
            if city_name:
                parts.append(city_name)
            if parts:
                return ", ".join(parts)

            return "Không rõ địa chỉ"

    def _get_feature_value(self, obj: Listing, feature_code: str) -> float | None:
        """
        Lấy giá trị của một feature dựa trên `code` của nó.
        Trả về một số float hoặc None.
        """
        try:
            # 1. Truy vấn bằng `feature__code` thay vì `feature__name`
            value_obj = obj.feature_values.get(feature__code=feature_code)

            # 2. Chuyển đổi giá trị một cách an toàn sang float
            return float(value_obj.value)

        except (ListingPropertyFeatureValue.DoesNotExist, ValueError, TypeError):
            # Bắt tất cả các lỗi có thể xảy ra và trả về None
            return None

    def get_beds(self, obj: Listing) -> int | None:
        # Gọi hàm helper với đúng `code`
        beds_float = self._get_feature_value(obj, 'NUM_BEDROOMS')
        # Chuyển đổi an toàn sang int nếu không phải là null
        return int(beds_float) if beds_float is not None else None

    def get_baths(self, obj: Listing) -> int | None:
        baths_float = self._get_feature_value(obj, 'NUM_BATHROOMS')
        return int(baths_float) if baths_float is not None else None

    def get_image_urls(self, obj: Listing) -> list[str]:
        if not hasattr(obj.property, 'media'):
            return []
        # Tối ưu: Lấy 4 ảnh đầu tiên
        media = obj.property.media.all()[:4]
        return [item.url.url for item in media if hasattr(item.url, 'url')]

    def get_total_image_count(self, obj: Listing) -> int:
        if not hasattr(obj.property, 'media'):
            return 0
        # TODO: Cần logic phân biệt ảnh/video dựa trên resource_type của Cloudinary
        return obj.property.media.all().count()

    def get_total_video_count(self, obj: Listing) -> int:
        # TODO: Logic phân biệt ảnh/video
        return 0

    def get_is_in_wishlist(self, obj: Listing) -> bool:
        """
        Kiểm tra xem tin đăng này có trong danh sách yêu thích của người dùng hiện tại không.
        """
        # Lấy user từ context của serializer
        request = self.context.get('request')

        # 2. Kiểm tra xem request và user có tồn tại và đã xác thực hay không
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Nếu có, thực hiện kiểm tra như bình thường
            return obj.wishlisted_by.filter(user=request.user).exists()

        return False

    def get_distance_km(self, obj: Listing) -> float | None:
        """
        Lấy khoảng cách đã được tính toán từ annotation trong queryset.
        """
        # 'distance' là tên trường chúng ta sẽ tạo bằng .annotate() trong view
        if hasattr(obj, 'distance'):
            # obj.distance là một đối tượng Distance của GeoDjango, có thuộc tính .km
            return round(obj.distance_km, 2)
        return None

class ListingDetailSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serializer chuyên dụng cho việc ĐỌC (hiển thị) dữ liệu Listing.
    Nó bao gồm các trường lồng nhau và các trường ảo được định dạng đẹp.
    """
    public_id = serializers.SerializerMethodField()

    user = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    property = PropertySerializer(read_only=True)

    # Hiển thị tên thay vì ID
    listing_type_name = serializers.CharField(source="listing_type.name", read_only=True)
    unit_price_name = serializers.CharField(source="unit_price.name", read_only=True, allow_null=True)
    unit_price_code = serializers.CharField(source="unit_price.code", read_only=True, allow_null=True)

    # Hiển thị giá đã được định dạng
    display_price = serializers.CharField(read_only=True)

    # Lồng danh sách các feature values
    feature_values = ListingPropertyFeatureValueSerializer(many=True, read_only=True)

    # Lồng các thông tin chi tiết (nếu có)
    buysell_detail = BuySellDetailSerializer(read_only=True)
    rental_detail = RentalDetailSerializer(read_only=True)
    project_detail = ProjectDetailSerializer(read_only=True)

    class Meta:
        model = Listing
        # Bao gồm tất cả các trường cần thiết để hiển thị chi tiết một tin đăng
        fields = [
            "public_id",
            "user",
            "property",
            "listing_type",
            "listing_type_name",
            "title",
            "content",
            "price_value",
            "unit_price_name",
            "unit_price_code",
            "display_price",
            "status",
            "spam_check_status",
            "commission_percentage",
            "created_date",
            "feature_values",
            "buysell_detail",
            "rental_detail",
            "project_detail",
        ]

    def get_public_id(self, obj):
        return hashids.encode(obj.id)

class PropertyCreateNestedSerializer(serializers.ModelSerializer):
    """Serializer con chỉ dùng để TẠO Property lồng nhau."""
    location = LocationSerializer() # Giữ nguyên

    property_type = serializers.SlugRelatedField(
        slug_field='code',
        queryset=PropertyType.objects.all()
    )
    direction = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Direction.objects.all(),
        required=False # Cho phép không bắt buộc
    )
    legal_status = serializers.SlugRelatedField(
        slug_field='code',
        queryset=LegalStatus.objects.all(),
        required=False # Cho phép không bắt buộc
    )

    class Meta:
        model = Property
        fields = [
            'property_type',
            'area',
            'direction',
            'legal_status',
            'location',
        ]

class FeatureInputSerializer(serializers.Serializer):
    feature_code = serializers.CharField()
    value = serializers.JSONField()

class VipPackageCreateSerializer(serializers.Serializer):
    """
    Serializer con để validate dữ liệu gói VIP khi tạo tin đăng.
    Nó không liên kết với model nào cả (không phải ModelSerializer).
    """
    vip_type_code = serializers.SlugRelatedField(
        slug_field='code',
        queryset=VipType.objects.filter(active=True),
        source='vip_type' # Khi validate thành công, validated_data sẽ có key 'vip_type' là một object VipType
    )
    duration_days = serializers.IntegerField(min_value=1, help_text="Số ngày mua VIP.")
    start_date = serializers.DateField(
        format="%Y-%m-%d",
        required=False, # Không bắt buộc, nếu thiếu sẽ lấy ngày hiện tại
        help_text="Ngày bắt đầu kích hoạt VIP (YYYY-MM-DD)."
    )

    def validate_start_date(self, value):
        """
        Kiểm tra để đảm bảo ngày bắt đầu không phải là một ngày trong quá khứ.
        """
        if value < date.today():
            raise serializers.ValidationError("Ngày bắt đầu không thể là một ngày trong quá khứ.")
        return value

class ListingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer chuyên dụng cho việc TẠO MỚI một Listing.
    Nó xử lý việc tạo lồng nhau Property (nếu cần) và các Detail liên quan.
    """

    # --- Trường để tạo mới Property (lồng nhau) ---
    # `required=False` để cho phép `property_id` được sử dụng thay thế
    property = PropertyCreateNestedSerializer(required=False)
    promotion_code = serializers.CharField(required=False, write_only=True, allow_blank=True)

    # --- Trường để liên kết với Property đã có ---
    # property_id = serializers.PrimaryKeyRelatedField(
    #     queryset=Property.objects.all(), write_only=True, required=False  # Không bắt buộc
    # )
    #
    # listing_type = serializers.SlugRelatedField(
    #     slug_field='code',
    #     queryset=ListingType.objects.all()
    # )

    listing_category_id = serializers.PrimaryKeyRelatedField(
        queryset=ListingCategory.objects.all(),
        write_only=True,
        source='category_temp'  # Lưu tạm vào một key không có trong model
    )

    unit_price = serializers.SlugRelatedField(
        slug_field='code',
        queryset=UnitPrice.objects.all()
    )

    # --- Các trường lồng nhau cho Details ---
    buysell_detail = BuySellDetailSerializer(required=False, write_only=True)
    rental_detail = RentalDetailSerializer(required=False, write_only=True)
    project_detail = ProjectDetailSerializer(required=False, write_only=True)

    features = FeatureInputSerializer(many=True, required=False, write_only=True)
    vip_package = VipPackageCreateSerializer(required=False, write_only=True)

    class Meta:
        model = Listing
        # Chỉ bao gồm các trường cần thiết để TẠO MỚI
        fields = [
            "listing_category_id",
            # "listing_type",
            "title",
            "content",
            "price_value",
            "unit_price",
            "commission_percentage",
            "property",  # Để tạo mới Property
            "property_id",  # Để liên kết Property
            "buysell_detail",  # Để tạo mới BuySellDetail
            "rental_detail",  # Để tạo mới RentalDetail
            "project_detail",  # Để tạo mới ProjectDetail
            "features",
            "vip_package",
            "promotion_code",
        ]

    def create(self, validated_data):
        # DRF đã tự động chuyển đổi các 'code' thành các object model đầy đủ
        # nên chúng ta không cần thay đổi gì nhiều ở đây.
        # Tuy nhiên, cần gọi service để xử lý logic tạo.
        category = validated_data.pop('category_temp')

        validated_data['listing_type'] = category.listing_type

        if 'property' in validated_data and validated_data['property']:
            validated_data['property']['property_type'] = category.property_type

        return listings_services.create_full_listing(
            user=self.context['request'].user,
            validated_data=validated_data
        )

    def validate_promotion_code(self, code):
        """
        Validate mã khuyến mãi ở cấp độ Serializer.
        """
        if not code:
            return code

        user = self.context['request'].user
        try:
            promo = UserPromotion.objects.get(
                code=code,
                user=user,
                status=UserPromotion.Status.AVAILABLE,
                expiry_date__gte=timezone.now()
            )
        except UserPromotion.DoesNotExist:
            raise serializers.ValidationError("Mã khuyến mãi không hợp lệ hoặc đã hết hạn.")

    def validate(self, data):
        """
        Kiểm tra logic nghiệp vụ phức tạp.
        """
        # 1. Đảm bảo người dùng cung cấp `property` hoặc `property_id`, nhưng không phải cả hai.
        has_property_data = "property" in data
        has_property_id = "property_id" in data

        if not has_property_data and not has_property_id:
            raise serializers.ValidationError(
                {"property_error": "Cần phải cung cấp 'property' (để tạo mới) hoặc 'property_id' (để liên kết)."}
            )

        if has_property_data and has_property_id:
            raise serializers.ValidationError("Không thể cung cấp đồng thời cả 'property' và 'property_id'.")

        # 2. Đảm bảo chỉ có một loại detail được cung cấp.
        detail_fields = ["buysell_detail", "rental_detail", "project_detail"]
        provided_details_count = sum(1 for field in detail_fields if field in data)
        if provided_details_count > 1:
            raise serializers.ValidationError(
                "Chỉ có thể cung cấp thông tin chi tiết cho một loại tin đăng (mua bán, cho thuê, hoặc dự án)."
            )

        return data