# tests/serializers/test_interactions/test_appointment_serializer.py
from datetime import timedelta

import pytest
from django.utils import timezone
from landifys.serializers.interactions import AppointmentSerializer


@pytest.mark.django_db
class TestAppointmentSerializer:
    """
    Bộ test case cho AppointmentSerializer.
    """

    def test_serialization_contains_expected_data(self, user_factory, appointment_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng các trường dữ liệu.
        """
        # ARRANGE
        user = user_factory()
        appointment = appointment_factory(user=user)

        # ACT
        serializer = AppointmentSerializer(instance=appointment)
        data = serializer.data

        # ASSERT
        expected_keys = {
            "id",
            "user",
            "listing",
            "appointment_date",
            "note",
            "status",
            "active",
            "created_date",
            "updated_date",
        }
        assert set(data.keys()) == expected_keys
        assert data["user"]["id"] == user.id
        # Kiểm tra các trường chỉ đọc
        assert "user" in AppointmentSerializer.Meta.read_only_fields
        assert "status" in AppointmentSerializer.Meta.read_only_fields
        # Kiểm tra trường write_only không xuất hiện
        assert "listing_id" not in data

    def test_deserialization_with_valid_data(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ để tạo mới.
        """
        # ARRANGE
        listing = listing_factory()
        future_date = timezone.now() + timedelta(days=2)
        valid_data = {"listing_id": listing.id, "appointment_date": future_date.isoformat(), "note": "A valid note."}

        # ACT
        serializer = AppointmentSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True

    def test_deserialization_with_invalid_date_format(self, listing_factory):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi định dạng ngày tháng không hợp lệ.
        """
        # ARRANGE
        listing = listing_factory()
        invalid_data = {
            "listing_id": listing.id,
            "appointment_date": "25-12-2025 10:00",  # Sai định dạng
            "note": "Invalid date format.",
        }

        # ACT
        serializer = AppointmentSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "appointment_date" in serializer.errors
        assert serializer.errors["appointment_date"][0].code == "invalid"
