import pytest
from unittest.mock import patch
from landifys.services import listings, ProtestResolutionError
from landifys.models import User, Property, Listing, Protest


@patch('landifys.tasks.listings.notify_user_of_protest_resolution.delay')
@pytest.mark.django_db
@pytest.mark.step_log
def test_resolve_protest_as_approved(mock_notify_user, log_step):
    """KỊCH BẢN: Thành công - Chấp thuận kháng nghị."""
    log_step("ARRANGE: Tạo admin, user, và một kháng nghị đang chờ xử lý.")
    admin = User.objects.create_user(username='admin', role=User.Role.ADMIN)
    user = User.objects.create_user(username='protester')
    prop = Property.objects.create(owner=user, area=1)
    listing = Listing.objects.create(user=user, property=prop, title='Listing', active=False)
    protest = Protest.objects.create(listing=listing, protester=user, status=Protest.Status.IN_PROGRESS)

    log_step("ACT: Admin chấp thuận kháng nghị.")
    resolved_protest = listings.resolve_protest(
        protest=protest, admin_user=admin, new_status=Protest.Status.RESOLVED, note="OK"
    )

    log_step("ASSERT: Trạng thái kháng nghị được cập nhật.")
    assert resolved_protest.status == Protest.Status.RESOLVED
    assert resolved_protest.admin == admin

    listing.refresh_from_db()
    log_step("ASSERT: Tin đăng được kích hoạt lại.")
    assert listing.active is True

    log_step("ASSERT: Tác vụ thông báo cho người dùng được kích hoạt.")
    mock_notify_user.assert_called_once_with(protest.id)
    log_step("=> PASSED!")

# ... (Bạn có thể thêm test case cho việc từ chối kháng nghị)