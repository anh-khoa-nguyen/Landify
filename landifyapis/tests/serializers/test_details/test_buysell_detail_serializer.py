# tests/serializers/test_details/test_buysell_detail_serializer.py
import pytest
from landifys.models import BuySellDetail
from landifys.serializers.details import BuySellDetailSerializer


@pytest.mark.django_db
class TestBuySellDetailSerializer:
    """
    Bộ test case cho BuySellDetailSerializer.
    """

    def test_serialization_contains_expected_fields(self, buy_sell_detail_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng các trường đã định nghĩa.
        """
        # ARRANGE: Sử dụng trực tiếp buysell_detail_factory.
        # Factory này sẽ tự động tạo ra một Listing liên quan.
        detail = buy_sell_detail_factory(condition_status=BuySellDetail.ConditionStatus.RENOVATED, is_mortgaged=True)

        # ACT
        serializer = BuySellDetailSerializer(instance=detail)
        data = serializer.data

        # ASSERT
        expected_keys = {"condition_status", "is_mortgaged"}
        assert set(data.keys()) == expected_keys
        assert data["condition_status"] == BuySellDetail.ConditionStatus.RENOVATED
        assert data["is_mortgaged"] is True

    def test_deserialization_with_valid_data(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer chấp nhận dữ liệu hợp lệ.
        """
        # ARRANGE
        valid_data = {"condition_status": "NEW", "is_mortgaged": False}

        # ACT
        serializer = BuySellDetailSerializer(data=valid_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
        # Kiểm tra dữ liệu đã được validate
        validated_data = serializer.validated_data
        assert validated_data["condition_status"] == BuySellDetail.ConditionStatus.NEW
        assert validated_data["is_mortgaged"] is False

    def test_deserialization_with_invalid_choice(self):
        """
        KỊCH BẢN: Thất bại - Deserialization
        Kiểm tra serializer báo lỗi khi 'condition_status' không hợp lệ.
        """
        # ARRANGE
        invalid_data = {"condition_status": "INVALID_STATUS", "is_mortgaged": True}  # Giá trị không có trong choices

        # ACT
        serializer = BuySellDetailSerializer(data=invalid_data)

        # ASSERT
        assert serializer.is_valid() is False
        assert "condition_status" in serializer.errors
        # Kiểm tra mã lỗi để chắc chắn đó là lỗi về lựa chọn không hợp lệ
        assert serializer.errors["condition_status"][0].code == "invalid_choice"

    def test_deserialization_allows_optional_fields(self):
        """
        KỊCH BẢN: Thành công - Deserialization
        Kiểm tra serializer vẫn hợp lệ khi các trường tùy chọn (nullable/blank) bị bỏ trống.
        """
        # ARRANGE: Dữ liệu trống, hợp lệ vì các trường trong model
        # BuySellDetail đều là nullable/blank.
        empty_data = {}

        # ACT
        serializer = BuySellDetailSerializer(data=empty_data)

        # ASSERT
        assert serializer.is_valid(raise_exception=True) is True
