from django.contrib.gis.geos import Point
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from vi_address.models import Ward

from apps.common.frontend_maps import choices_maps, feature_maps
from apps.common.mixins import DynamicFieldsMixin
from apps.users.serializers import UserSerializer

from ..common.services import BusinessLogicError
from . import services as property_services
from .models import Direction, Location, Property, PropertyFeature, PropertyMedia, PropertyType

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
        if obj.feature_type == "TEXT":
            return choices_maps.get_feature_choices(obj.code)
        return None


class LocationSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    point = GeometryField(read_only=True)

    ward = serializers.PrimaryKeyRelatedField(queryset=Ward.objects.all(), write_only=True, required=True)

    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = Location
        fields = [
            "id",
            "street",
            "point",
            "ward",
            "ward_name",
            "district_name",
            "city_name",
            "latitude",
            "longitude",
        ]


class PropertyMediaSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model PropertyMedia."""

    file = serializers.FileField(write_only=True, required=False)

    files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.url:
            rep["url"] = instance.url.url
        return rep

    class Meta:
        model = PropertyMedia
        fields = ["id", "url", "public_id", "property", "file", "files", "media_type", "source_url"]
        read_only_fields = ["id", "url", "public_id", "property", "media_type", "source_url"]


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
            #"property_type",
            #"direction",
            #"legal_status",
            "property_type_name",
            "direction_name",
            "legal_status_name",
            "media",
        ]

    extra_kwargs = {
        'property_type': {'write_only': True, 'required': True},
        'direction': {'write_only': True, 'required': False, 'allow_null': True},
        'legal_status': {'write_only': True, 'required': False, 'allow_null': True},
    }

    def create(self, validated_data):
        location_data = validated_data.pop("location")

        # 1. Lấy và xóa 'latitude', 'longitude' khỏi dictionary
        latitude = location_data.pop("latitude", None)
        longitude = location_data.pop("longitude", None)

        # 2. Nếu có cả hai, tạo đối tượng Point và thêm vào dictionary
        if latitude is not None and longitude is not None:
            location_data["point"] = Point(longitude, latitude, srid=4326)

        # 3. Tạo Location object với dictionary đã được xử lý
        location = Location.objects.create(**location_data)

        owner = self.context["request"].user
        prop = Property.objects.create(owner=owner, location=location, **validated_data)
        return prop

    def update(self, instance, validated_data):
        if "location" in validated_data:
            location_data = validated_data.pop("location")
            # Tương tự, chúng ta cũng cần xử lý lat/lng cho update
            latitude = location_data.pop("latitude", None)
            longitude = location_data.pop("longitude", None)
            if latitude is not None and longitude is not None:
                location_data["point"] = Point(longitude, latitude, srid=4326)

            location_serializer = LocationSerializer(instance.location, data=location_data, partial=True)
            location_serializer.is_valid(raise_exception=True)
            location_serializer.save()

        return super().update(instance, validated_data)
