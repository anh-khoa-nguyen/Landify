import pytest
from landifys.services import listings
from landifys.models import User, Property, Listing, PropertyFeature, ListingPropertyFeatureValue


@pytest.mark.django_db
@pytest.mark.step_log
def test_update_listing_features(log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra việc thêm mới, cập nhật và xóa các đặc điểm của tin đăng.
    """
    log_step("ARRANGE: Tạo dữ liệu nền (user, listing, features).")
    user = User.objects.create_user(username='testuser')
    prop = Property.objects.create(owner=user, area=1)
    listing = Listing.objects.create(user=user, property=prop, title='Test Listing')

    feature_phong_ngu = PropertyFeature.objects.create(name='Số phòng ngủ', feature_type='FLOAT')
    feature_ban_cong = PropertyFeature.objects.create(name='Hướng ban công', feature_type='TEXT')
    feature_do_xe = PropertyFeature.objects.create(name='Có chỗ đỗ xe', feature_type='BOOLEAN')

    # Gán giá trị ban đầu: 2 phòng ngủ, có chỗ đỗ xe
    ListingPropertyFeatureValue.objects.create(listing=listing, feature=feature_phong_ngu, value=2)
    ListingPropertyFeatureValue.objects.create(listing=listing, feature=feature_do_xe, value=True)

    log_step("ARRANGE: Chuẩn bị dữ liệu mới: 3 phòng ngủ, hướng Đông, không đề cập chỗ đỗ xe.")
    new_features_data = [
        {'feature_id': feature_phong_ngu.id, 'value': 3.0},  # Cập nhật
        {'feature_id': feature_ban_cong.id, 'value': 'Đông'}  # Thêm mới
        # Feature 'Có chỗ đỗ xe' bị loại bỏ
    ]

    log_step("ACT: Gọi service update_listing_features.")
    listings.update_listing_features(listing=listing, features_data=new_features_data)

    log_step("ASSERT: Tin đăng bây giờ chỉ có 2 đặc điểm.")
    assert listing.feature_values.count() == 2

    log_step("ASSERT: Đặc điểm 'Số phòng ngủ' đã được cập nhật thành 3.")
    pn_value = ListingPropertyFeatureValue.objects.get(listing=listing, feature=feature_phong_ngu)
    assert pn_value.value == 3.0

    log_step("ASSERT: Đặc điểm 'Hướng ban công' đã được thêm mới.")
    bc_value = ListingPropertyFeatureValue.objects.get(listing=listing, feature=feature_ban_cong)
    assert bc_value.value == 'Đông'

    log_step("ASSERT: Đặc điểm 'Có chỗ đỗ xe' đã bị xóa.")
    assert not ListingPropertyFeatureValue.objects.filter(listing=listing, feature=feature_do_xe).exists()
    log_step("=> PASSED!")