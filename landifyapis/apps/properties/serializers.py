from rest_framework import serializers
from vi_address.models import Ward
from django.contrib.gis.geos import Point

from apps.common.mixins import DynamicFieldsMixin
from apps.common.frontend_maps import feature_maps
from apps.users.serializers import UserSerializer
from .models import Location, PropertyFeature, PropertyMedia, Property, PropertyType, Direction

from . import services as property_services
from apps.common.frontend_maps import feature_maps, choices_maps
from ..common.services import BusinessLogicError

# ==============================================================================
# COMPONENT & NESTED SERIALIZERS
# ==============================================================================
# Các serializer này là những thành phần xây dựng nên PropertySerializer chính.
# Chúng đại diện cho các model liên quan như Feature, Location, và Media.

class PropertyFeatureSerializer(serializers.ModelSerializer):
    """
    Serializer cho PropertyFeature.
    Làm giàu dữ liệu với các thông tin cho frontend (icon, group, unit).
    """

    icon_code = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    choices = serializers.SerializerMethodField()

    class Meta:
        model = PropertyFeature
        fields = ["id", "name", "code", "category", "feature_type", "icon_code", "unit", "choices"]

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

    def get_choices(self, obj: PropertyFeature) -> list | None:
        if obj.feature_type == 'TEXT':
             return choices_maps.get_feature_choices(obj.code)
        return None

class LocationSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(), write_only=True, required=True
    )

    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = Location
        fields = [
            "id", "street", "point", "ward", "ward_name",
            "district_name", "city_name",
            "latitude", "longitude",
        ]

    def create(self, validated_data):
        # Lấy và xóa lat/lng ra khỏi validated_data để chúng không được
        # truyền trực tiếp vào Location.objects.create()
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)

        # Nếu cả lat và lng đều được cung cấp
        if latitude is not None and longitude is not None:
            # Tạo một đối tượng Point từ GeoDjango
            # Lưu ý: Point nhận vào (longitude, latitude)
            validated_data['point'] = Point(longitude, latitude, srid=4326)

        # Gọi hàm create gốc với validated_data đã được cập nhật
        return super().create(validated_data)

class PropertyMediaSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model PropertyMedia."""

    file = serializers.FileField(write_only=True, required=False)

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

# ==============================================================================
# CORE PROPERTY SERIALIZER
# ==============================================================================
# Serializer chính cho model Property, được sử dụng trong PropertyViewSet.
# Nó lồng các component serializer ở trên để có một cấu trúc dữ liệu hoàn chỉnh.

class PropertySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Property, xử lý việc tạo/cập nhật Location lồng nhau."""

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

        return super().update(instance, validated_data)