# tests/serializers/test_listings/test_property_serializer.py
import pytest
from landifys.serializers.listings import PropertySerializer
from landifys.models import Location, Property
from types import SimpleNamespace

@pytest.mark.django_db
class TestPropertySerializer:
    def test_serialization_contains_nested_location(self, property_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng dữ liệu lồng nhau của location và owner.
        """
        # ARRANGE
        # Tạo một property với location có street là "Main St"
        prop = property_factory(owner__first_name="John", location__street="Main St")

        # ACT
        serializer = PropertySerializer(instance=prop)
        data = serializer.data

        # ASSERT
        assert "location" in data
        assert data['location']['street'] == "Main St"
        # Kiểm tra xem các trường suy diễn có được serialize đúng không
        # (Giả sử LocationSerializer của bạn đã được cập nhật)
        assert data['location']['ward_name'] == prop.location.ward.name
        assert data['location']['district_name'] == prop.location.district.name
        assert data['location']['city_name'] == prop.location.city.name

        assert data['owner']['get_full_name'] == prop.owner.get_full_name()

    def test_create_with_nested_location(self, user_factory, property_type_factory, ward_factory):
        """
        KỊCH BẢN: Thành công - Create
        Kiểm tra phương thức create tạo thành công Property và Location
        khi chỉ cần cung cấp 'ward_id'.
        """
        # ARRANGE
        user = user_factory()
        prop_type = property_type_factory()
        # Chỉ cần tạo một Ward, không cần City hay District riêng lẻ nữa
        ward = ward_factory()

        request = SimpleNamespace()
        request.user = user
        context = {'request': request}

        # Dữ liệu gửi lên giờ đây đơn giản hơn rất nhiều
        valid_data = {
            "property_type_id": prop_type.id,
            "area": 120.5,
            "location": {
                "street": "456 Nguyễn Huệ",
                # CHỈ CẦN CUNG CẤP ward_id
                "ward": ward.id,
            }
        }

        # ACT
        serializer = PropertySerializer(data=valid_data, context=context)
        serializer.is_valid(raise_exception=True)
        prop = serializer.save()

        # ASSERT
        assert Property.objects.count() == 1
        assert Location.objects.count() == 1
        assert prop.location is not None
        assert prop.location.street == "456 Nguyễn Huệ"
        assert prop.location.ward == ward
        # Kiểm tra các thuộc tính suy diễn
        assert prop.location.district == ward.parent_code
        assert prop.location.city == ward.parent_code.parent_code
        assert prop.owner == user