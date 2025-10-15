# tests/serializers/test_listings/test_location_serializer.py
import pytest
from landifys.models import Location
from landifys.serializers.listings import LocationSerializer


@pytest.mark.django_db
class TestLocationSerializer:

    def test_serialization_returns_derived_names(self, location_factory, ward_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng tên phường, quận, thành phố được suy ra
        từ mối quan hệ khóa ngoại của Ward.
        """
        # ARRANGE
        # Tạo một ward với district và city cụ thể để kiểm tra
        ward = ward_factory(
            name="Phường Bến Nghé", parent_code__name="Quận 1", parent_code__parent_code__name="TP. Hồ Chí Minh"
        )
        # Tạo location trỏ đến ward này
        location = location_factory(ward=ward)

        # ACT
        serializer = LocationSerializer(instance=location)
        data = serializer.data

        # ASSERT
        expected_keys = {"id", "street", "point", "ward_name", "district_name", "city_name"}
        # Kiểm tra xem các trường write_only (ward_id) không có trong output
        assert set(data.keys()) == expected_keys

        # Kiểm tra các giá trị được suy diễn
        assert data["ward_name"] == "Phường Bến Nghé"
        assert data["district_name"] == "Quận 1"
        assert data["city_name"] == "TP. Hồ Chí Minh"

    def test_deserialization_with_valid_ward_id(self, ward_factory):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận 'ward_id' hợp lệ để tạo mới.
        """
        # ARRANGE
        ward = ward_factory()
        valid_data = {
            "street": "123 Lê Lợi",
            "ward": ward.id,
        }

        # ACT
        serializer = LocationSerializer(data=valid_data)
        assert serializer.is_valid(raise_exception=True) is True
        assert serializer.validated_data["ward"] == ward

    def test_deserialization_fails_without_ward_id(self):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi thiếu trường bắt buộc 'ward_id'.
        """
        # ARRANGE
        invalid_data = {
            "street": "123 Lê Lợi",
        }

        # ACT
        serializer = LocationSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "ward" in serializer.errors
        assert serializer.errors["ward"][0].code == "required"

    def test_deserialization_ignores_extra_ids(self, ward_factory):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer vẫn hợp lệ và bỏ qua các trường 'district_id', 'city_id'
        nếu chúng được gửi lên.
        """
        # ARRANGE
        ward = ward_factory()
        data_with_extra_fields = {
            "street": "123 Lê Lợi",
            "ward": ward.id,
            "district_id": 999,  # Dữ liệu thừa
            "city_id": 888,  # Dữ liệu thừa
        }

        # ACT
        serializer = LocationSerializer(data=data_with_extra_fields)

        # ASSERT
        # Serializer vẫn valid vì các trường thừa không được định nghĩa trong serializer
        # để ghi, nên chúng sẽ bị bỏ qua.
        assert serializer.is_valid(raise_exception=True) is True
        # Kiểm tra validated_data không chứa các key thừa
        assert "district_id" not in serializer.validated_data
        assert "city_id" not in serializer.validated_data
