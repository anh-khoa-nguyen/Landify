# tests/serializers/test_details/test_project_detail_serializer.py
import pytest
from landifys.serializers.details import ProjectDetailSerializer


@pytest.mark.django_db
class TestProjectDetailSerializer:
    """
    Bộ test case cho ProjectDetailSerializer.
    """

    def test_serialization_contains_all_fields(self, project_detail_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về tất cả các trường đã định nghĩa.
        """
        # ARRANGE
        detail = project_detail_factory(developer="Vingroup")

        # ACT
        serializer = ProjectDetailSerializer(instance=detail)
        data = serializer.data

        # ASSERT
        expected_keys = {
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
        }
        assert set(data.keys()) == expected_keys
        assert data["developer"] == "Vingroup"

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ.
        """
        # ARRANGE
        valid_data = {
            "developer": "Masterise Homes",
            "total_area": "271 ha",
            "building_density": 25.5,
            "scale_description": "Gồm 72 tòa tháp cao từ 25 đến 35 tầng",
            "total_units": 10000,
            "unit_area_range": "30m² - 100m²",
            "ownership_form": "Sổ hồng lâu dài",
            "launch_date": "2025-01-15",
            "handover_date": "2027-06-30",
        }

        # ACT
        serializer = ProjectDetailSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
