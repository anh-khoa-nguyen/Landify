from django.db import transaction

from apps.common.tasks import notifications
from apps.common.services import BusinessLogicError, ProtestResolutionError
#from apps.common.tasks import notifications as moderation_tasks
from apps.listings.models import Listing
from apps.users.models import User

from .models import Protest
from .serializers import ProtestSerializer

def create_protest_for_listing(
    *, listing: Listing, protester: User, serializer: ProtestSerializer
) -> Protest:
    if listing.active:
        raise BusinessLogicError("Chỉ có thể kháng nghị các tin đăng không hoạt động.")
    if Protest.objects.filter(listing=listing, status=Protest.Status.IN_PROGRESS).exists():
        raise BusinessLogicError("Tin đăng này đã có một kháng nghị đang chờ xử lý.")

    protest = serializer.save(protester=protester, listing=listing)
    notifications.notify_admins_of_new_protest.delay(protest.id)
    return protest

def resolve_protest(*, protest: Protest, admin_user: User, new_status: str, note: str) -> Protest:
    """Hàm dịch vụ để xử lý một kháng nghị."""
    if new_status not in [Protest.Status.RESOLVED, Protest.Status.REJECTED]:
        raise ProtestResolutionError("Trạng thái xử lý không hợp lệ.")
    if protest.status != Protest.Status.IN_PROGRESS:
        raise ProtestResolutionError(
            f"Kháng nghị này đã được xử lý trước đó với trạng thái: {protest.get_status_display()}."
        )

    with transaction.atomic():
        protest.status = new_status
        protest.resolution_note = note
        protest.admin = admin_user
        protest.save()

        if new_status == Protest.Status.RESOLVED:
            listing = protest.listing
            listing.active = True
            listing.spam_check_status = Listing.SpamCheckStatus.CLEAN
            listing.save(update_fields=["active", "spam_check_status"])

    notifications.notify_user_of_protest_resolution.delay(protest.id)
    return protest