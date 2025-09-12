# tests/serializers/test_listings/test_property_media_serializer.py
import pytest
from landifys.serializers.listings import PropertyMediaSerializer

@pytest.mark.django_db
class TestPropertyMediaSerializer:
    """
    Bộ test case cho PropertyMediaSerializer.
    """

    def test_serialization_contains_expected_fields(self, property_media_factory):
        """
        KỊCH BẢN: Thành công - Serialization
        Kiểm tra serializer trả về đúng các trường dữ liệu.
        """
        # ARRANGE
        media = property_media_factory(
            url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
            public_id="sample"
        )

        # ACT
        serializer = PropertyMediaSerializer(instance=media)
        data = serializer.data

        # ASSERT
        expected_keys = {
            "id", "property", "url", "public_id",
            "active", "created_date", "updated_date"
        }
        assert set(data.keys()) == set(expected_keys)
        assert data['url'] == "https://res.cloudinary.com/demo/image/upload/sample.jpg"
        assert data['public_id'] == "sample"
        assert data['property'] == media.property.id

    def test_read_only_fields_are_not_writable(self):
        """
        KỊCH BẢN: Thành công
        Kiểm tra các trường chỉ đọc không thể được ghi vào khi deserialize.
        """
        # ARRANGE
        # Dữ liệu đầu vào chứa các trường chỉ đọc
        invalid_data = {
            "url": "http://new-url.com",
            "property": 99, # Cố gắng gán vào trường chỉ đọc
            "public_id": "new_public_id" # Cố gắng gán vào trường chỉ đọc
        }

        # ACT
        serializer = PropertyMediaSerializer(data=invalid_data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # ASSERT
        # Các trường chỉ đọc không có mặt trong validated_data
        assert "property" not in validated_data
        assert "public_id" not in validated_data
        # Trường có thể ghi vẫn tồn tại
        assert "url" in validated_data