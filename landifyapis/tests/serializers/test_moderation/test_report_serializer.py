# tests/serializers/test_moderation/test_report_serializer.py
import pytest
from landifys.models import Report
from landifys.serializers.moderation import ReportSerializer


@pytest.mark.django_db
class TestReportSerializer:
    """
    Bộ test case cho ReportSerializer.
    """

    def test_serialization_contains_expected_data(self, user_factory, report_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng cấu trúc JSON với dữ liệu user lồng nhau.
        """
        # ARRANGE
        reporter = user_factory(first_name="Good", last_name="Citizen")
        report = report_factory(
            reporter=reporter,
            reported_item_type=Report.ItemType.LISTING,
            reported_item_id=123,
            description="Tin đăng này có dấu hiệu lừa đảo.",
        )

        # ACT
        serializer = ReportSerializer(instance=report)
        data = serializer.data

        # ASSERT
        expected_keys = {
            "id",
            "reporter",
            "description",
            "status",
            "reported_item_id",
            "reported_item_type",
            "active",
            "created_date",
            "updated_date",
        }
        assert set(data.keys()) == expected_keys
        assert data["reporter"]["get_full_name"] == "Good Citizen"
        assert data["reported_item_type"] == Report.ItemType.LISTING
        assert data["reported_item_id"] == 123

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ để tạo mới.
        """
        # ARRANGE
        valid_data = {
            "reported_item_type": "user",
            "reported_item_id": 456,
            "description": "Người dùng này có hành vi không phù hợp.",
        }

        # ACT
        serializer = ReportSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True

    def test_deserialization_fails_with_invalid_item_type(self):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi 'reported_item_type' không hợp lệ.
        """
        # ARRANGE
        invalid_data = {
            "reported_item_type": "invalid_type",  # Giá trị không có trong choices
            "reported_item_id": 789,
            "description": "Test invalid type.",
        }

        # ACT
        serializer = ReportSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "reported_item_type" in serializer.errors
        assert serializer.errors["reported_item_type"][0].code == "invalid_choice"

    def test_read_only_fields_are_not_writable(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra các trường chỉ đọc không thể được ghi vào.
        """
        # ARRANGE
        data = {
            "reported_item_type": "post",
            "reported_item_id": 1,
            "description": "Some description.",
            "status": Report.Status.RESOLVED,  # Cố gắng ghi vào trường chỉ đọc
            "reporter": 99,  # Cố gắng ghi vào trường chỉ đọc
        }

        # ACT
        serializer = ReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # ASSERT
        assert "status" not in validated_data
        assert "reporter" not in validated_data
