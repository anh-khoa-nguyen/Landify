import pytest
from django.utils import timezone
from landifys.services import interactions, BusinessLogicError
from landifys.models import User, Property, Listing, Appointment


# Sử dụng fixture của pytest để tạo dữ liệu dùng chung cho nhiều test
@pytest.fixture
def appointment_setup():
    owner = User.objects.create_user(username='owner')
    requester = User.objects.create_user(username='requester')
    admin = User.objects.create_user(username='admin', role=User.Role.ADMIN)
    prop = Property.objects.create(owner=owner, area=1)
    listing = Listing.objects.create(user=owner, property=prop, title='Test')
    appointment = Appointment.objects.create(
        user=requester,
        listing=listing,
        appointment_date=timezone.now(),
        status=Appointment.Status.PENDING
    )
    return owner, requester, admin, appointment


@pytest.mark.django_db
@pytest.mark.step_log
def test_owner_can_confirm_appointment(appointment_setup, log_step):
    """KỊCH BẢN: Thành công - Chủ tin đăng xác nhận lịch hẹn."""
    owner, _, _, appointment = appointment_setup

    log_step("ACT: Chủ tin đăng cập nhật trạng thái thành CONFIRMED.")
    updated_appointment = interactions.update_appointment_status(
        appointment=appointment,
        new_status=Appointment.Status.CONFIRMED,
        actor=owner
    )

    log_step("ASSERT: Trạng thái của lịch hẹn đã được cập nhật.")
    assert updated_appointment.status == Appointment.Status.CONFIRMED
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log
def test_requester_cannot_confirm_appointment(appointment_setup, log_step):
    """KỊCH BẢN: Thất bại - Người đặt hẹn không thể tự xác nhận."""
    _, requester, _, appointment = appointment_setup

    log_step("ACT & ASSERT: Người đặt hẹn cố gắng xác nhận và kiểm tra lỗi.")
    with pytest.raises(BusinessLogicError, match="Chỉ chủ tin đăng hoặc quản trị viên mới có thể xác nhận lịch hẹn."):
        interactions.update_appointment_status(
            appointment=appointment,
            new_status=Appointment.Status.CONFIRMED,
            actor=requester
        )
    log_step("=> PASSED!")


@pytest.mark.django_db
@pytest.mark.step_log
def test_any_involved_party_can_cancel(appointment_setup, log_step):
    """KỊCH BẢN: Thành công - Các bên liên quan đều có thể hủy lịch."""
    owner, requester, admin, appointment = appointment_setup

    log_step("--- Trường hợp 1: Người đặt hẹn hủy ---")
    interactions.update_appointment_status(
        appointment=appointment,
        new_status=Appointment.Status.CANCELLED,
        actor=requester
    )
    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.CANCELLED

    log_step("--- Trường hợp 2: Chủ tin đăng hủy ---")
    # Reset trạng thái để test
    appointment.status = Appointment.Status.PENDING
    appointment.save()
    interactions.update_appointment_status(
        appointment=appointment,
        new_status=Appointment.Status.CANCELLED,
        actor=owner
    )
    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.CANCELLED

    log_step("=> PASSED!")