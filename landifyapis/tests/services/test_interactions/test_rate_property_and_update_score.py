import pytest
# VVV THÊM IMPORT NÀY VVV
from landifys.serializers.interactions import ReviewSerializer
from landifys.services import interactions
from landifys.models import User, Property, Review, UserProfile


@pytest.mark.django_db
@pytest.mark.step_log
def test_rate_property_and_update_score(log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra việc tạo đánh giá và cập nhật điểm trung bình cho chủ sở hữu.
    """
    log_step("ARRANGE: Tạo chủ sở hữu, người đánh giá và 2 BĐS.")
    owner = User.objects.create_user(username='owner')
    UserProfile.objects.create(user=owner)
    reviewer1 = User.objects.create_user(username='reviewer1')
    reviewer2 = User.objects.create_user(username='reviewer2')

    prop1 = Property.objects.create(owner=owner, area=1)
    prop2 = Property.objects.create(owner=owner, area=2)

    log_step("--- Lượt 1: Đánh giá 5 sao cho BĐS 1 ---")
    log_step("ARRANGE: Chuẩn bị dữ liệu và serializer thật cho đánh giá đầu tiên.")
    # VVV THAY ĐỔI KHỐI NÀY VVV
    review_data1 = {'rating': 5, 'comment': 'Tuyệt vời!'}
    serializer1 = ReviewSerializer(data=review_data1)
    assert serializer1.is_valid() is True

    log_step("ACT: Gọi service với serializer thật.")
    interactions.rate_property_and_update_score(user=reviewer1, prop=prop1, serializer=serializer1)

    owner.profile.refresh_from_db()
    log_step("ASSERT: Điểm của chủ sở hữu là 5.0, số lượt đánh giá là 1.")
    assert owner.profile.rating_score == 5.0
    assert owner.profile.rating_count == 1
    log_step("ASSERT: Một bản ghi Review đã được tạo trong CSDL.")
    assert Review.objects.count() == 1

    log_step("--- Lượt 2: Đánh giá 3 sao cho BĐS 2 ---")
    log_step("ARRANGE: Chuẩn bị dữ liệu và serializer thật cho đánh giá thứ hai.")
    # VVV THAY ĐỔI KHỐI NÀY VVV
    review_data2 = {'rating': 3, 'comment': 'Tạm ổn.'}
    serializer2 = ReviewSerializer(data=review_data2)
    assert serializer2.is_valid() is True

    log_step("ACT: Gọi service với serializer thật.")
    interactions.rate_property_and_update_score(user=reviewer2, prop=prop2, serializer=serializer2)

    owner.profile.refresh_from_db()
    log_step("ASSERT: Điểm trung bình của chủ sở hữu được cập nhật thành (5+3)/2 = 4.0.")
    assert owner.profile.rating_score == 4.0
    log_step("ASSERT: Số lượt đánh giá được cập nhật thành 2.")
    assert owner.profile.rating_count == 2
    log_step("ASSERT: Tổng số bản ghi Review bây giờ là 2.")
    assert Review.objects.count() == 2
    log_step("=> PASSED!")