# apps/listings/option_serializers.py
from rest_framework import serializers
from apps.properties.models import PropertyType, Direction, LegalStatus, PropertyFeature
from .models import UnitPrice, VipType, UserPromotion, ListingType, ListingCategory
from apps.properties.serializers import PropertyFeatureSerializer
from ..common.frontend_maps import property_type_maps, direction_maps, legal_status_maps


class PropertyTypeOptionSerializer(serializers.ModelSerializer):
    icon_code = serializers.SerializerMethodField()

    class Meta:
        model = PropertyType
        fields = ['code', 'name', 'icon_code']

    def get_icon_code(self, obj: PropertyType) -> str:
        return property_type_maps.get_property_type_frontend_info(obj.code).get('icon_code')

class ListingCategoryOptionSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị các lựa chọn danh mục hợp lệ, đã được nhóm lại.
    """
    # Sử dụng CharField và trỏ source đến property `display_name`
    name = serializers.CharField(source='display_name', read_only=True)
    property_type_code = serializers.CharField(source='property_type.code')

    class Meta:
        model = ListingCategory
        # ID cần thiết để client gửi lên khi tạo tin
        fields = ['id', 'name', 'property_type_code']

class ListingTypeOptionSerializer(serializers.ModelSerializer):
    """
    Serializer đơn giản để cung cấp các lựa chọn Nhu cầu (Bán/Cho thuê).
    """
    class Meta:
        model = ListingType
        # Chỉ lấy 2 trường mà frontend cần để hiển thị và xử lý logic
        fields = ['code', 'name']
# ====================================

class DirectionOptionSerializer(serializers.ModelSerializer):
    icon_code = serializers.SerializerMethodField()

    class Meta:
        model = Direction
        fields = ['code', 'name', 'icon_code'] # Giả sử bạn sẽ thêm trường 'code' vào model Direction

    def get_icon_code(self, obj: Direction) -> str:
        return direction_maps.get_direction_frontend_info(obj.code).get('icon_code')

class LegalStatusOptionSerializer(serializers.ModelSerializer):
    icon_code = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    color_hex = serializers.SerializerMethodField()

    class Meta:
        model = LegalStatus
        fields = ['code', 'name', 'icon_code', 'description', 'color_hex'] # Giả sử bạn sẽ thêm trường 'code' vào model LegalStatus

    def get_icon_code(self, obj: LegalStatus) -> str:
        return legal_status_maps.get_legal_status_frontend_info(obj.code).get('icon_code')

    def get_description(self, obj: LegalStatus) -> str:
        return legal_status_maps.get_legal_status_frontend_info(obj.code).get('description')

    def get_color_hex(self, obj: LegalStatus) -> str:
        return legal_status_maps.get_legal_status_frontend_info(obj.code).get('color_hex')

class UnitPriceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitPrice
        fields = ['code', 'name']


class VipTypeOptionSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị các lựa chọn gói VIP cho frontend.
    """
    class Meta:
        model = VipType
        # Chỉ trả về các trường mà frontend thực sự cần
        fields = [
            'name',
            'code',
            'price_per_day',
            'sort_priority',
            # Các trường tùy chỉnh để "chế biến" sẵn cho frontend
            'subtitle', # Sẽ được thêm bằng SerializerMethodField
            'benefit_tag', # Sẽ được thêm bằng SerializerMethodField
        ]

    # === THÊM CÁC TRƯỜNG "CHẾ BIẾN" DỮ LIỆU ===
    subtitle = serializers.SerializerMethodField()
    benefit_tag = serializers.SerializerMethodField()

    def get_subtitle(self, obj: VipType) -> str:
        # Logic để tạo phụ đề dựa trên độ ưu tiên
        if obj.sort_priority >= 100:
            return "Hiển thị trên cùng"
        elif obj.sort_priority >= 50:
            return "Dưới VIP Kim Cương"
        else:
            return "Hiển thị nổi bật"

    def get_benefit_tag(self, obj: VipType) -> str:
        # Logic để tạo tag lợi ích dựa trên hệ số nhân
        if obj.boost_multiplier > 1:
            return f"x{obj.boost_multiplier} lượt liên hệ so với tin thường"
        return "Tăng khả năng tiếp cận"


class UserPromotionOptionSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị các khuyến mãi cụ thể mà người dùng đang có.
    Nó lấy thông tin từ cả UserPromotion và PromotionRule liên quan.
    """
    # --- Lấy các trường trực tiếp từ PromotionRule ---
    title = serializers.CharField(source='rule.title', read_only=True)
    description = serializers.CharField(source='rule.description', read_only=True)
    promo_type = serializers.CharField(source='rule.promo_type', read_only=True)
    free_listing_days = serializers.IntegerField(source='rule.free_listing_days', read_only=True)
    discount_percentage = serializers.FloatField(source='rule.discount_percentage', read_only=True)

    # Lấy danh sách code của các VipType được áp dụng từ PromotionRule
    applicable_vip_type_codes = serializers.SlugRelatedField(
        source='rule.applicable_vip_types',
        many=True,
        read_only=True,
        slug_field='code'
    )

    class Meta:
        model = UserPromotion
        # Các trường cần hiển thị cho frontend
        fields = [
            # Từ UserPromotion
            'code',  # Mã code duy nhất mà người dùng sẽ sử dụng
            'expiry_date',  # Ngày hết hạn cụ thể của người dùng này
            'status',

            # Từ PromotionRule (thông qua `source`)
            'title',
            'description',
            'promo_type',
            'free_listing_days',
            'discount_percentage',
            'applicable_vip_type_codes',
        ]