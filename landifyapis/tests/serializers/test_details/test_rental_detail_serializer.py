# tests/serializers/test_details/test_rental_detail_serializer.py
import pytest
from decimal import Decimal
from landifys.serializers.details import RentalDetailSerializer

@pytest.mark.django_db
class TestRentalDetailSerializer:
    """
    Bộ test case cho RentalDetailSerializer.
    """

    def test_serialization_contains_all_fields(self, rental_detail_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về tất cả các trường đã định nghĩa.
        """
        # ARRANGE
        detail = rental_detail_factory(deposit_amount=Decimal("10000000.00"))

        # ACT
        serializer = RentalDetailSerializer(instance=detail)
        data = serializer.data

        # ASSERT
        expected_keys = {
            "deposit_amount", "min_lease_duration", "allow_pets", "allow_smoking",
            "max_occupants", "is_electricity_included", "is_water_included",
            "is_internet_included", "is_management_fee_included", "available_from_date"
        }
        assert set(data.keys()) == expected_keys
        assert data['deposit_amount'] == "10000000.00" # DecimalField được serialize thành string

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận các kiểu dữ liệu hợp lệ.
        """
        # ARRANGE
        valid_data = {
            "deposit_amount": "15000000.50",
            "min_lease_duration": 12,
            "allow_pets": True,
            "allow_smoking": False,
            "max_occupants": 4,
            "is_electricity_included": True,
            "is_water_included": False,
            "is_internet_included": True,
            "is_management_fee_included": False,
            "available_from_date": "2025-12-01"
        }

        # ACT
        serializer = RentalDetailSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True