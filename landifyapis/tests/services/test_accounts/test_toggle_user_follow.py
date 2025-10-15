# landifys/tests/test_accounts/test_toggle_user_follow.py

import pytest
from landifys.models import Subscription, User
from landifys.services import BusinessLogicError, accounts


@pytest.mark.django_db
@pytest.mark.step_log  # <<< ĐÁNH DẤU TEST NÀY
def test_user_cannot_follow_themselves(log_step):  # <<< INJECT FIXTURE VÀO ĐÂY
    """
    KỊCH BẢN 1: Thất bại
    Kiểm tra rằng hệ thống sẽ ném ra lỗi BusinessLogicError
    khi một người dùng cố gắng tự theo dõi chính mình.
    """
    log_step("ARRANGE: Tạo một người dùng 'testuser'.")
    user = User.objects.create_user(username="testuser")

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception được ném ra.")
    with pytest.raises(BusinessLogicError) as excinfo:
        accounts.toggle_user_follow(follower=user, following=user)

    log_step("ASSERT: Kiểm tra nội dung của thông điệp lỗi.")
    assert str(excinfo.value) == "Bạn không thể tự theo dõi chính mình."
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log  # <<< ĐÁNH DẤU TEST NÀY
def test_toggle_follow_creates_and_deletes_subscription(log_step):  # <<< INJECT FIXTURE VÀO ĐÂY
    """
    KỊCH BẢN 2: Thành công
    Kiểm tra rằng việc gọi toggle_user_follow:
    - Lần 1: Sẽ tạo ra một đối tượng Subscription trong database.
    - Lần 2: Sẽ xóa đi đối tượng Subscription đó.
    """
    log_step("ARRANGE: Tạo 2 người dùng 'usera' và 'userb'.")
    user_a = User.objects.create_user(username="usera")
    user_b = User.objects.create_user(username="userb")

    log_step("--- Lượt 1: Follow ---")
    log_step("ACT: user_a theo dõi user_b.")
    status1 = accounts.toggle_user_follow(follower=user_a, following=user_b)

    log_step("ASSERT: Trạng thái trả về là 'followed'.")
    assert status1 == "followed"
    log_step("ASSERT: Một bản ghi Subscription tồn tại trong CSDL.")
    assert Subscription.objects.filter(follower=user_a, following=user_b).exists() is True
    assert Subscription.objects.count() == 1

    log_step("--- Lượt 2: Unfollow ---")
    log_step("ACT: user_a gọi lại hàm để bỏ theo dõi user_b.")
    status2 = accounts.toggle_user_follow(follower=user_a, following=user_b)

    log_step("ASSERT: Trạng thái trả về là 'unfollowed'.")
    assert status2 == "unfollowed"
    log_step("ASSERT: Bản ghi Subscription đã bị xóa khỏi CSDL.")
    assert Subscription.objects.filter(follower=user_a, following=user_b).exists() is False
    assert Subscription.objects.count() == 0
    log_step("=> PASSED!")
