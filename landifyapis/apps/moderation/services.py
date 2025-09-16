from django.db import transaction

from apps.common.tasks import notifications
from apps.common.services import BusinessLogicError, ProtestResolutionError
#from apps.common.tasks import notifications as moderation_tasks
from apps.listings.models import Listing
from apps.users.models import User

from .models import Protest, ModerationAction, Report
from .serializers import ProtestSerializer


# === SERVICE MỚI: Thực hiện một hành động xử lý ===
def take_moderation_action(*, moderator: User, report: Report, action_type: str, reason: str) -> ModerationAction:
    """
    Thực hiện một hành động xử lý dựa trên một báo cáo.
    Hàm này sẽ vô hiệu hóa nội dung và tạo một bản ghi ModerationAction.
    """
    target_object = report.reported_object
    if not hasattr(target_object, 'active'):
        raise BusinessLogicError("Đối tượng này không thể bị vô hiệu hóa.")

    with transaction.atomic():
        # 1. Vô hiệu hóa nội dung (ví dụ: gỡ tin đăng)
        target_object.active = False
        target_object.save(update_fields=['active'])

        # 2. Cập nhật trạng thái của báo cáo
        report.status = Report.Status.ACTION_TAKEN
        report.save(update_fields=['status'])

        # 3. Tạo bản ghi hành động để làm bằng chứng
        action = ModerationAction.objects.create(
            report=report,
            moderator=moderator,
            action_type=action_type,
            reason=reason,
            target_object=target_object
        )

    # 4. Gửi thông báo cho người dùng bị ảnh hưởng
    # (Ví dụ: thông báo tin đăng của họ đã bị gỡ)
    # ... (thêm logic gọi task thông báo ở đây) ...

    return action


def create_protest(*, action: ModerationAction, protester: User, reason: str) -> Protest:
    """Tạo một kháng nghị cho một hành động xử lý."""
    # Kiểm tra xem người kháng nghị có phải là chủ sở hữu của nội dung không
    target_owner = getattr(action.target_object, 'user', None) or getattr(action.target_object, 'owner', None)
    if protester != target_owner:
        raise BusinessLogicError("Bạn không có quyền kháng nghị cho hành động này.")

    if hasattr(action, 'protest'):
        raise BusinessLogicError("Hành động này đã được kháng nghị trước đó.")

    protest = Protest.objects.create(
        action=action,
        protester=protester,
        reason=reason
    )

    # Gửi thông báo cho các admin về kháng nghị mới
    title = f"Kháng nghị mới cho hành động #{action.id}"
    content = f"Người dùng '{protester.username}' đã gửi kháng nghị. Vui lòng xem xét."
    related_item = {"type": "protest", "id": protest.id}
    notifications.send_notification_to_admins.delay(
        category="new_protest", title=title, content=content, related_item=related_item
    )

    return protest

def resolve_protest(*, protest: Protest, admin_user: User, new_status: str, note: str) -> Protest:
    """Xử lý một kháng nghị (chấp thuận hoặc từ chối)."""
    if new_status not in [Protest.Status.RESOLVED, Protest.Status.REJECTED]:
        raise BusinessLogicError("Trạng thái xử lý không hợp lệ.")
    if protest.status != Protest.Status.IN_PROGRESS:
        raise BusinessLogicError("Kháng nghị này đã được xử lý trước đó.")

    with transaction.atomic():
        protest.status = new_status
        protest.resolution_note = note
        protest.admin_reviewer = admin_user
        protest.save()

        # Nếu chấp thuận kháng nghị -> Khôi phục lại nội dung
        if new_status == Protest.Status.RESOLVED:
            target_object = protest.action.target_object
            if hasattr(target_object, 'active'):
                target_object.active = True
                target_object.save(update_fields=['active'])
                # (Tùy chọn) Tạo một ModerationAction khác loại RESTORE_CONTENT để ghi lại

    # Gửi thông báo kết quả cho người dùng
    title = f"Kháng nghị của bạn cho hành động #{protest.action.id} đã được xử lý"
    content = f"Kết quả: {protest.get_status_display()}.\nGhi chú: {note}"
    related_item = {"type": "protest", "id": protest.id}  # Hoặc trỏ về đối tượng gốc
    notifications.send_notification_to_user.delay(
        user_id=protest.protester_id,
        category="protest_resolution",
        title=title,
        content=content,
        related_item=related_item
    )

    return protest