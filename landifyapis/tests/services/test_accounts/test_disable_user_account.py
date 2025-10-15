import pytest
from landifys.models import User
from landifys.services import BusinessLogicError, accounts


@pytest.mark.django_db
@pytest.mark.step_log
def test_admin_cannot_disable_themselves(log_step):
    """KỊCH BẢN: Thất bại - Admin không thể tự vô hiệu hóa mình."""
    log_step("ARRANGE: Tạo một admin.")
    admin_user = User.objects.create_user(username="admin", role=User.Role.ADMIN)

    log_step("ACT & ASSERT: Kiểm tra exception khi admin tự vô hiệu hóa.")
    with pytest.raises(BusinessLogicError, match="Không thể vô hiệu hóa tài khoản này."):
        accounts.disable_user_account(admin_user=admin_user, user_to_disable=admin_user)
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log
def test_disable_and_reenable_user(log_step):
    """KỊCH BẢN: Thành công - Vô hiệu hóa và kích hoạt lại người dùng."""
    log_step("ARRANGE: Tạo một admin và một người dùng thường đang hoạt động.")
    admin_user = User.objects.create_user(username="admin", role=User.Role.ADMIN)
    regular_user = User.objects.create_user(username="testuser", is_active=True)

    log_step("--- Lượt 1: Vô hiệu hóa ---")
    log_step("ACT: Admin vô hiệu hóa người dùng.")
    new_status1 = accounts.disable_user_account(admin_user=admin_user, user_to_disable=regular_user)

    log_step("ASSERT: Trạng thái trả về là False (không hoạt động).")
    assert new_status1 is False
    regular_user.refresh_from_db()
    log_step("ASSERT: Cờ is_active trong CSDL của người dùng là False.")
    assert regular_user.is_active is False

    log_step("--- Lượt 2: Kích hoạt lại ---")
    log_step("ACT: Admin kích hoạt lại người dùng.")
    new_status2 = accounts.disable_user_account(admin_user=admin_user, user_to_disable=regular_user)

    log_step("ASSERT: Trạng thái trả về là True (hoạt động).")
    assert new_status2 is True
    regular_user.refresh_from_db()
    log_step("ASSERT: Cờ is_active trong CSDL của người dùng là True.")
    assert regular_user.is_active is True
    log_step("=> PASSED!")
