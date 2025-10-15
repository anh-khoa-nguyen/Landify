from unittest.mock import patch

import pytest
from landifys.models import Listing, ListingType, Location, Property, PropertyType, User
from landifys.services import BusinessLogicError, listings


@patch("landifys.tasks.listings.check_listing_for_spam.delay")
@pytest.mark.django_db
@pytest.mark.step_log
def test_create_listing_with_new_property(mock_check_spam, log_step):
    """
    KỊCH BẢN 1: Thành công - Tạo tin đăng kèm BĐS mới.
    """
    log_step("ARRANGE: Tạo người dùng và các đối tượng phụ trợ (PropertyType).")
    user = User.objects.create_user(username="owner")
    prop_type = PropertyType.objects.create(name="Căn hộ")
    listing_type_ban = ListingType.objects.create(name="Bán")

    log_step("ARRANGE: Chuẩn bị dữ liệu validated từ serializer.")
    validated_data = {
        "title": "Bán căn hộ",
        "listing_type": listing_type_ban,
        "property": {  # Dữ liệu để tạo Property mới
            "property_type": prop_type,
            "area": 50.0,
            "location": {"street": "123 ABC"},
        },
    }

    log_step("ACT: Gọi service create_full_listing.")
    new_listing = listings.create_full_listing(user=user, validated_data=validated_data)

    log_step("ASSERT: 1 Listing, 1 Property, 1 Location đã được tạo.")
    assert Listing.objects.count() == 1
    assert Property.objects.count() == 1
    assert Location.objects.count() == 1

    log_step("ASSERT: Các đối tượng được liên kết chính xác.")
    assert new_listing.user == user
    assert new_listing.property.owner == user

    log_step("ASSERT: Tác vụ kiểm tra spam được gọi với ID của tin đăng mới.")
    mock_check_spam.assert_called_once_with(new_listing.id)
    log_step("=> PASSED!")


@patch("landifys.tasks.listings.check_listing_for_spam.delay")
@pytest.mark.django_db
@pytest.mark.step_log
def test_create_listing_for_existing_property(mock_check_spam, log_step):
    """
    KỊCH BẢN 2: Thành công - Tạo tin đăng cho BĐS đã có.
    """
    log_step("ARRANGE: Tạo người dùng và một BĐS đã tồn tại của họ.")
    user = User.objects.create_user(username="owner")
    existing_property = Property.objects.create(owner=user, area=100.0)
    listing_type_thue = ListingType.objects.create(name="Cho Thuê")

    log_step("ARRANGE: Chuẩn bị dữ liệu validated.")
    validated_data = {
        "title": "Cho thuê BĐS có sẵn",
        "listing_type": listing_type_thue,
        "property": existing_property,  # Dữ liệu là object Property đã có
    }

    log_step("ACT: Gọi service.")
    listings.create_full_listing(user=user, validated_data=validated_data)

    log_step("ASSERT: 1 Listing mới được tạo.")
    assert Listing.objects.count() == 1
    log_step("ASSERT: KHÔNG có Property mới nào được tạo.")
    assert Property.objects.count() == 1

    log_step("ASSERT: Tin đăng mới được liên kết với BĐS đã có.")
    assert Listing.objects.first().property == existing_property
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log
def test_create_listing_for_unowned_property_fails(log_step):
    """
    KỊCH BẢN 3: Thất bại - Cố tạo tin đăng cho BĐS của người khác.
    """
    log_step("ARRANGE: Tạo 2 người dùng và 1 BĐS của 'owner'.")
    owner = User.objects.create_user(username="owner")
    imposter = User.objects.create_user(username="imposter")
    owners_property = Property.objects.create(owner=owner, area=100.0)

    log_step("ARRANGE: Chuẩn bị dữ liệu validated.")
    validated_data = {"title": "Tin đăng trái phép", "listing_type": 1, "property": owners_property}

    log_step("ACT & ASSERT: Gọi service với tư cách 'imposter' và kiểm tra lỗi.")
    with pytest.raises(BusinessLogicError, match="Bạn không có quyền đăng tin cho bất động sản này."):
        listings.create_full_listing(user=imposter, validated_data=validated_data)
    log_step("=> PASSED!")
