from unittest.mock import MagicMock, patch

import pytest
from landifys.models import Listing, Property, Protest, User
from landifys.services import BusinessLogicError, listings


@patch("landifys.tasks.listings.notify_admins_of_new_protest.delay")
@pytest.mark.django_db
@pytest.mark.step_log
def test_create_protest_successfully(mock_notify_admins, log_step):
    """KỊCH BẢN: Thành công - Tạo kháng nghị cho tin đăng không hoạt động."""
    log_step("ARRANGE: Tạo user và tin đăng không hoạt động.")
    user = User.objects.create_user(username="protester")
    prop = Property.objects.create(owner=user, area=1)
    listing = Listing.objects.create(user=user, property=prop, title="Listing", active=False)

    log_step("ARRANGE: Tạo mock serializer.")
    mock_serializer = MagicMock()
    # Giả lập hàm save của serializer trả về một đối tượng Protest đã được tạo
    mock_serializer.save.return_value = Protest(protester=user, listing=listing, reason="Test")

    log_step("ACT: Gọi service.")
    listings.create_protest_for_listing(listing=listing, protester=user, serializer=mock_serializer)

    log_step("ASSERT: Hàm save của serializer được gọi.")
    mock_serializer.save.assert_called_once_with(protester=user, listing=listing)

    log_step("ASSERT: Tác vụ thông báo cho admin được kích hoạt.")
    mock_notify_admins.assert_called_once()
    log_step("=> PASSED!")


# ... (Bạn có thể thêm các test case thất bại cho tin đăng đang active, hoặc đã có protest)
