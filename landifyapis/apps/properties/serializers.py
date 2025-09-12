from rest_framework import serializers
from vi_address.models import Ward

from apps.common.mixins import DynamicFieldsMixin
from apps.common.frontend_maps import feature_maps
from apps.users.serializers import UserSerializer
from .models import Location, PropertyFeature, PropertyMedia, Property, PropertyType, Direction

from . import services as property_services
from apps.common.frontend_maps import feature_maps
from ..common.services import BusinessLogicError


# ==============================================================================
# FEATURE & PROPERTY SERIALIZERS
# ==============================================================================

class LocationSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = Location
        fields = [
            "id", "street", "point", "ward", "ward_name",
            "district_name", "city_name",
        ]

class PropertyFeatureSerializer(serializers.ModelSerializer):
    """
    Serializer cho PropertyFeature.
    Làm giàu dữ liệu với các thông tin cho frontend (icon, group, unit).
    """

    icon_code = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    class Meta:
        model = PropertyFeature
        fields = ["id", "name", "code", "category", "feature_type", "icon_code", "unit",]

    def get_frontend_info(self, obj: PropertyFeature) -> dict:
        """Hàm helper để tra cứu thông tin frontend và cache kết quả."""
        cache_key = f"frontend_info_{obj.code}"

        if cache_key in self.context:
            return self.context[cache_key]

        info = feature_maps.get_feature_frontend_info(obj.code)
        # ==============================

        self.context[cache_key] = info
        return info

    def get_icon_code(self, obj: PropertyFeature) -> str:
        return self.get_frontend_info(obj).get("icon_code")

    def get_display_group(self, obj: PropertyFeature) -> str:
        return self.get_frontend_info(obj).get("display_group", "")

    def get_unit(self, obj: PropertyFeature) -> str | None:
        return self.get_frontend_info(obj).get("unit")

class PropertyMediaSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model PropertyMedia."""
    file = serializers.FileField(write_only=True, required=False)

    # Thêm một trường files để nhận nhiều file
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.url:
            rep['url'] = instance.url.url
        return rep

    class Meta:
        model = PropertyMedia
        fields = ['id', 'url', 'public_id', 'property', 'file', 'files']
        read_only_fields = ["id", "url", "public_id", "property"]

class PropertySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Property, xử lý việc tạo/cập nhật Location lồng nhau."""
    # CÁC TRƯỜNG CHỈ ĐỌC (READ-ONLY)
    owner = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    location = LocationSerializer()
    property_type_name = serializers.CharField(source="property_type.name", read_only=True)
    direction_name = serializers.CharField(source="direction.name", read_only=True, allow_null=True)
    legal_status_name = serializers.CharField(source="legal_status.name", read_only=True, allow_null=True)
    media = PropertyMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "owner",
            "location",
            "area",
            "property_type_name",
            "direction_name",
            "legal_status_name",
            "media"
        ]

    extra_kwargs = {
        'property_type': {'write_only': True, 'required': True},
        'direction': {'write_only': True, 'required': False},
        'legal_status': {'write_only': True, 'required': False},
    }

    def create(self, validated_data):
        location_data = validated_data.pop("location")
        location = Location.objects.create(**location_data)
        owner = self.context["request"].user
        prop = Property.objects.create(owner=owner, location=location, **validated_data)
        return prop

    def update(self, instance, validated_data):
        if "location" in validated_data:
            location_data = validated_data.pop("location")
            location_serializer = LocationSerializer(instance.location, data=location_data, partial=True)
            location_serializer.is_valid(raise_exception=True)
            location_serializer.save()

        # DRF sẽ tự động xử lý việc cập nhật các trường còn lại (property_type, direction...)
        return super().update(instance, validated_data)