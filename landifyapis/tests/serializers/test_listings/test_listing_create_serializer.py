# tests/serializers/test_listings/test_listing_create_serializer.py
import pytest
from rest_framework.exceptions import ValidationError
from landifys.serializers.listings import ListingCreateSerializer


@pytest.mark.django_db
class TestListingCreateSerializer:

    def test_validation_fails_if_no_property_provided(self):
        """
        KỊCH BẢN: Thất bại - Validation
        Kiểm tra serializer báo lỗi khi không cung cấp 'property' hoặc 'property_id'.
        """
        invalid_data = {
            "title": "Test Listing",
            "content": "Some content."
        }
        serializer = ListingCreateSerializer(data=invalid_data)

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "property_error" in excinfo.value.detail

    def test_validation_fails_if_both_properties_provided(self, property_factory, listing_type_factory, ward_factory):
        """
        KỊCH BẢN: Thất bại - Validation
        Kiểm tra serializer báo lỗi khi cung cấp cả 'property' và 'property_id'.
        """
        # ARRANGE
        prop = property_factory()
        l_type = listing_type_factory()
        ward = ward_factory()  # Cần ward để tạo location hợp lệ

        # Dữ liệu không hợp lệ: chứa cả property_id và một dictionary property HỢP LỆ TỐI THIỂU
        invalid_data = {
            "listing_type": l_type.id,
            "title": "Test Listing",
            "content": "Some content here.",

            "property_id": prop.id,  # Tham số thứ nhất

            # Tham số thứ hai: Cung cấp một dictionary 'property' hợp lệ
            # để nó vượt qua vòng validation của PropertySerializer
            "property": {
                "property_type_id": prop.property_type.id,
                "area": 150.0,
                "location": {
                    "street": "789 Tôn Đức Thắng",
                    "ward": ward.id
                }
            }
        }

        # ACT
        serializer = ListingCreateSerializer(data=invalid_data)

        # ASSERT
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        # Bây giờ, validation của các trường riêng lẻ đã pass,
        # DRF sẽ chạy đến hàm validate() chung và báo lỗi non_field_errors.
        assert "non_field_errors" in excinfo.value.detail
        assert "Không thể cung cấp đồng thời cả 'property' và 'property_id'." in str(excinfo.value)

    def test_validation_fails_if_multiple_details_provided(self, property_factory, listing_type_factory):
        """
        KỊCH BẢN: Thất bại - Validation
        Kiểm tra serializer báo lỗi khi cung cấp nhiều hơn một loại detail.
        """
        prop = property_factory()
        l_type = listing_type_factory()
        invalid_data = {
            "title": "Test Listing",
            # THÊM CÁC TRƯỜNG BẮT BUỘC CÒN THIẾU
            "content": "Some content here.",
            "listing_type": l_type.id,
            # -----------------------------------
            "property_id": prop.id,
            "buysell_detail": {"is_mortgaged": False},
            "rental_detail": {"deposit_amount": 5000000}
        }
        serializer = ListingCreateSerializer(data=invalid_data)

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "non_field_errors" in excinfo.value.detail

    def test_valid_data_with_property_id(self, property_factory, listing_type_factory):
        """
        KỊCH BẢN: Thành công - Validation
        Kiểm tra serializer hợp lệ khi liên kết với một property đã có.
        """
        prop = property_factory()
        l_type = listing_type_factory()
        valid_data = {
            "title": "Valid Listing",
            # THÊM CÁC TRƯỜNG BẮT BUỘC CÒN THIẾU
            "content": "This is a valid content.",
            "listing_type": l_type.id,
            # -----------------------------------
            "property_id": prop.id,
            "buysell_detail": {"is_mortgaged": True}
        }
        serializer = ListingCreateSerializer(data=valid_data)
        assert serializer.is_valid(raise_exception=True) is True