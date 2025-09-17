# apps/properties/serializers.py
from datetime import date
from django.contrib.humanize.templatetags.humanize import intcomma
from apps.common.models import GeoGridStatistic # Đảm bảo import đúng model mới
from apps.common.utils.geogrid import geogrid_converter # Import converter

from django.utils import timezone
from rest_framework import serializers
from vi_address.models import Ward
from . import constants # Import file constants của bạn

from apps.common.mixins import DynamicFieldsMixin
from apps.common.frontend_maps import feature_maps
from apps.users.serializers import UserSerializer
from apps.properties.serializers import PropertySerializer, PropertyFeatureSerializer, LocationSerializer
from apps.common.utils.hashids import hashids
from apps.properties.models import Property, PropertyType, PropertyFeature, Direction, LegalStatus

from .models import ListingPropertyFeatureValue, Listing, ListingType, UnitPrice, VipType, UserPromotion, \
    ListingCategory
# from .models import BuySellDetail, ProjectDetail, RentalDetail
from . import services as listings_services

# ==============================================================================
# SERIALIZER CHO CÁC THÀNH PHẦN PHỤ / HELPER
# ==============================================================================
# Các serializer nhỏ, dùng để lồng vào các serializer lớn hơn.

class ListingPropertyFeatureValueSerializer(serializers.ModelSerializer):
    """Serializer cho bảng trung gian, lồng thông tin chi tiết của Feature."""

    feature = PropertyFeatureSerializer(read_only=True)

    class Meta:
        model = ListingPropertyFeatureValue
        fields = ["feature", "value"]

# ==============================================================================
# SERIALIZER ĐỌC DỮ LIỆU (READ / OUTPUT)
# ==============================================================================
# Các serializer này chuyên để định dạng và trả dữ liệu về cho client.

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
    price_analysis = serializers.SerializerMethodField()

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
            "price_analysis"
        ]

    def get_public_id(self, obj):
        return hashids.encode(obj.id)

    def get_price_analysis(self, obj: Listing) -> dict | None:
        """
        Phân tích giá của tin đăng so với giá trung bình trong ô lưới địa lý tương ứng.
        Dữ liệu trung bình được lấy từ bảng GeoGridStatistic đã được tính toán trước.
        """
        # 1. Kiểm tra các điều kiện cần thiết
        location = obj.property.location
        if not location or not location.point or not obj.price_value:
            return None  # Không có tọa độ hoặc giá thì không thể phân tích

        # 2. Chuyển đổi tọa độ của BĐS thành ID của ô lưới
        cell_id = geogrid_converter.get_cell_id(location.point.y, location.point.x)
        if not cell_id:
            return None

        try:
            # 3. Truy vấn cực nhanh đến bảng thống kê bằng khóa chính (cell_id)
            stats = GeoGridStatistic.objects.get(pk=cell_id)

            avg_price = None
            unit_text = ""
            area_name = "khu vực lân cận"  # Tên chung chung, không còn phụ thuộc Phường/Xã

            # 4. Xác định loại hình để lấy đúng giá trung bình
            listing_type_code = obj.listing_category.listing_type.code

            # --- Trường hợp CHO THUÊ ---
            if listing_type_code == 'RENT' and stats.avg_rent_price and stats.rent_listing_count > 1:
                avg_price = stats.avg_rent_price
                unit_text = "VND/tháng"

            # --- Trường hợp MUA BÁN (chỉ xét giá /m²) ---
            elif (listing_type_code == 'BUY_SELL' and
                  obj.unit_price and obj.unit_price.code == 'PER_M2' and
                  stats.avg_sell_price_per_m2 and stats.sell_listing_count > 1):
                avg_price = stats.avg_sell_price_per_m2
                unit_text = "/m²"

            # Nếu không rơi vào các trường hợp trên, hoặc không có đủ dữ liệu (count <= 1)
            if avg_price is None:
                return {"message": "Chưa có đủ dữ liệu để so sánh giá tại khu vực này."}

            # 5. Tính toán chênh lệch và đưa ra nhận định
            difference = float(obj.price_value) - float(avg_price)
            percentage = (difference / float(avg_price)) * 100

            assessment = "tương đương"
            if percentage > 15:
                assessment = "cao hơn đáng kể"
            elif percentage > 5:
                assessment = "cao hơn một chút"
            elif percentage < -15:
                assessment = "thấp hơn đáng kể"
            elif percentage < -5:
                assessment = "thấp hơn một chút"

            # 6. Định dạng kết quả trả về cho frontend
            return {
                "area_name": area_name,
                "average_price_formatted": f"{intcomma(int(avg_price))} {unit_text}",
                "difference_percentage": round(percentage, 1),
                "assessment": assessment,
                "listing_count": stats.rent_listing_count if listing_type_code == 'RENT' else stats.sell_listing_count,
            }

        except GeoGridStatistic.DoesNotExist:
            return {"message": "Chưa có đủ dữ liệu để so sánh giá tại khu vực này."}

# ==============================================================================
# SERIALIZER GHI DỮ LIỆU (CREATE / UPDATE)
# ==============================================================================
# Các serializer này chuyên để nhận, validate và xử lý dữ liệu đầu vào từ client.

class FeatureInputSerializer(serializers.Serializer):
    """Serializer để nhận dữ liệu feature đầu vào khi tạo/cập nhật listing."""
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

class PropertyCreateNestedSerializer(serializers.ModelSerializer):
    """Serializer con chỉ dùng để TẠO Property lồng nhau."""
    location = LocationSerializer() # Giữ nguyên

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
        fields = ['area', 'direction', 'legal_status', 'location']

class ListingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer chuyên dụng cho việc TẠO MỚI một Listing.
    Nó xử lý việc tạo lồng nhau Property (nếu cần) và các Detail liên quan.
    """

    property = PropertyCreateNestedSerializer(required=False)
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(), write_only=True, required=False  # Không bắt buộc
    )

    listing_category = serializers.PrimaryKeyRelatedField(
        queryset=ListingCategory.objects.select_related('listing_type', 'property_type').all(),
        write_only=True,
    )

    unit_price = serializers.SlugRelatedField(
        slug_field='code',
        queryset=UnitPrice.objects.all()
    )
    features = FeatureInputSerializer(many=True, required=False, write_only=True)
    vip_package = VipPackageCreateSerializer(required=False, write_only=True)
    promotion_code = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = Listing
        # Chỉ bao gồm các trường cần thiết để TẠO MỚI
        fields = [
            "listing_category",
            "title",
            "content",
            "price_value",
            "unit_price",
            "commission_percentage",
            "property",  # Để tạo mới Property
            "property_id",  # Để liên kết Property
            "features",
            "vip_package",
            "promotion_code",
        ]

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

        return data

    def validate_features(self, features_data):
        """
        Thực hiện validation chi tiết cho từng feature được gửi lên.
        """
        if not features_data:
            return features_data

        # 1. Tối ưu hóa: Lấy tất cả các feature codes và objects cần thiết trong 1-2 query
        feature_codes = [item.get('feature_code') for item in features_data if item.get('feature_code')]
        features_map = {f.code: f for f in PropertyFeature.objects.filter(code__in=feature_codes)}

        # Helper map để liên kết code của feature với class hằng số tương ứng
        choice_constants_map = {
            "CONDITION_STATUS": constants.ConditionStatus,
            "INTERIOR_STATUS": constants.InteriorStatus,
        }

        # 2. Lặp qua từng feature người dùng gửi lên để kiểm tra
        for item in features_data:
            code = item.get('feature_code')
            value = item.get('value')

            feature_obj = features_map.get(code)

            # Kiểm tra xem feature code có tồn tại không
            if not feature_obj:
                raise serializers.ValidationError(f"Đặc điểm với mã '{code}' không tồn tại.")

            # 3. Kiểm tra giá trị dựa trên feature_type
            feature_type = feature_obj.feature_type

            if feature_type == PropertyFeature.FeatureType.FLOAT:
                if not isinstance(value, (int, float)):
                    raise serializers.ValidationError(f"Đặc điểm '{feature_obj.name}' yêu cầu một giá trị số.")

            elif feature_type == PropertyFeature.FeatureType.BOOLEAN:
                if not isinstance(value, bool):
                    raise serializers.ValidationError(f"Đặc điểm '{feature_obj.name}' yêu cầu giá trị true hoặc false.")

            elif feature_type == PropertyFeature.FeatureType.DIRECTION:
                if not isinstance(value, int) or not Direction.objects.filter(pk=value).exists():
                    raise serializers.ValidationError(f"Đặc điểm '{feature_obj.name}' yêu cầu một ID Hướng hợp lệ.")

            elif feature_type == PropertyFeature.FeatureType.TEXT:
                constant_class = choice_constants_map.get(code)
                if constant_class:
                    # Lấy tất cả các giá trị hợp lệ từ class hằng số
                    allowed_values = [getattr(constant_class, attr) for attr in dir(constant_class) if
                                      not attr.startswith('__')]
                    if value not in allowed_values:
                        raise serializers.ValidationError(
                            f"Giá trị '{value}' không hợp lệ cho đặc điểm '{feature_obj.name}'. "
                            f"Các giá trị được chấp nhận là: {', '.join(allowed_values)}."
                        )
                # Nếu không có trong map, nó là một trường text tự do, không cần validate thêm

        return features_data

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