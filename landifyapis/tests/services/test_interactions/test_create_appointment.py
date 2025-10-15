from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from landifys.models import Appointment, Listing, Property, User
from landifys.services import BusinessLogicError, interactions


@pytest.mark.django_db
@pytest.mark.step_log
def test_create_appointment_in_the_past_fails(log_step):
    """KỊCH BẢN: Thất bại - Cố gắng tạo lịch hẹn trong quá khứ."""
    log_step("ARRANGE: Tạo user, listing.")
    user = User.objects.create_user(username="testuser")
    prop = Property.objects.create(owner=user, area=1)
    listing = Listing.objects.create(user=user, property=prop, title="Test")

    log_step("ARRANGE: Tạo một thời điểm trong quá khứ.")
    past_date = timezone.now() - timedelta(days=1)

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(BusinessLogicError, match="Không thể đặt lịch hẹn trong quá khứ."):
        interactions.create_appointment(user=user, listing=listing, appointment_date=past_date, note="Test")
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log
def test_create_appointment_successfully(log_step):
    """KỊCH BẢN: Thành công - Tạo lịch hẹn hợp lệ."""
    log_step("ARRANGE: Tạo user, listing.")
    user = User.objects.create_user(username="testuser")
    prop = Property.objects.create(owner=user, area=1)
    listing = Listing.objects.create(user=user, property=prop, title="Test")

    log_step("ARRANGE: Tạo một thời điểm trong tương lai.")
    future_date = timezone.now() + timedelta(days=5)

    log_step("ACT: Gọi service.")
    appointment = interactions.create_appointment(
        user=user, listing=listing, appointment_date=future_date, note="Hẹn gặp"
    )

    log_step("ASSERT: Một đối tượng Appointment được tạo trong CSDL.")
    assert Appointment.objects.count() == 1

    log_step("ASSERT: Thông tin lịch hẹn được lưu chính xác.")
    assert appointment.user == user
    assert appointment.listing == listing
    assert appointment.appointment_date == future_date
    assert appointment.status == Appointment.Status.PENDING
    log_step("=> PASSED!")
