# tests/serializers/test_listings/test_listing_serializer.py
from decimal import Decimal

import pytest
from landifys.models import ListingPropertyFeatureValue, PropertyFeature  # <-- Thêm import
from landifys.serializers.listings import ListingSerializer
from landifys.serializers.utils import hashids  # Import hashids để kiểm tra


@pytest.mark.django_db
class TestListingSerializer:
    """
    Bộ test case cho ListingSerializer (chuyên về serialization).
    """

    def test_serialization_contains_all_nested_objects(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Cấu trúc lồng nhau
        Kiểm tra serializer trả về đầy đủ các đối tượng lồng nhau như
        user, property, location, details...
        """
        # ARRANGE
        # Tạo một listing với các đối tượng liên quan để kiểm tra
        listing = listing_factory(
            user__first_name="John",
            property__location__street="123 Main St",
            buysell_detail__is_mortgaged=True,  # Tạo luôn detail liên quan
        )
        # Thêm một feature vào listing
        # 1. Tạo đối tượng PropertyFeature trước
        feature = PropertyFeature.objects.create(name="Số phòng ngủ", feature_type="FLOAT")

        # 2. Tạo đối tượng ListingPropertyFeatureValue một cách tường minh
        #    và liên kết nó với listing và feature đã có.
        ListingPropertyFeatureValue.objects.create(listing=listing, feature=feature, value=3.0)

        # ACT
        serializer = ListingSerializer(instance=listing)
        data = serializer.data

        # ASSERT
        # Kiểm tra các key cấp cao nhất
        expected_keys = {
            "public_id",
            "user",
            "property",
            "listing_type",
            "listing_type_name",
            "title",
            "content",
            "price_value",
            "unit_price",
            "unit_price_name",
            "display_price",
            "status",
            "spam_check_status",
            "commission_percentage",
            "created_date",
            "feature_values",
            "buysell_detail",
            "rental_detail",
            "project_detail",
        }
        assert set(data.keys()) == expected_keys

        # Kiểm tra dữ liệu lồng nhau
        assert data["user"]["get_full_name"] == listing.user.get_full_name()
        assert data["property"]["location"]["street"] == "123 Main St"
        assert data["buysell_detail"]["is_mortgaged"] is True
        assert data["rental_detail"] is None  # Phải là null vì không được tạo

        # Kiểm tra feature_values
        assert len(data["feature_values"]) == 1
        assert data["feature_values"][0]["feature"]["name"] == "Số phòng ngủ"
        assert data["feature_values"][0]["value"] == 3.0

    def test_public_id_is_correctly_encoded(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Trường ảo public_id
        Kiểm tra SerializerMethodField 'public_id' mã hóa ID thật một cách chính xác.
        """
        # ARRANGE
        listing = listing_factory()
        expected_public_id = hashids.encode(listing.id)

        # ACT
        serializer = ListingSerializer(instance=listing)
        data = serializer.data

        # ASSERT
        assert data["public_id"] == expected_public_id

    def test_display_price_serialization(self, listing_factory, unit_price_factory):
        """
        KỊCH BẢN: Thành công - Trường ảo display_price
        Kiểm tra property 'display_price' được serialize đúng.
        """
        # ARRANGE
        unit = unit_price_factory(name="tỷ")
        listing = listing_factory(price_value=Decimal("5.50"), unit_price=unit)

        # ACT
        serializer = ListingSerializer(instance=listing)
        data = serializer.data

        # ASSERT
        # Dựa trên logic của @property trong model của bạn
        assert data["display_price"] == "5.5 tỷ"

    def test_display_price_for_negotiable_price(self, listing_factory):
        """
        KỊCH BẢN: Thành công - Giá thỏa thuận
        Kiểm tra 'display_price' trả về "Giá thỏa thuận" khi không có giá.
        """
        # ARRANGE
        listing = listing_factory(price_value=None, unit_price=None)

        # ACT
        serializer = ListingSerializer(instance=listing)
        data = serializer.data

        # ASSERT
        assert data["display_price"] == "Giá thỏa thuận"
