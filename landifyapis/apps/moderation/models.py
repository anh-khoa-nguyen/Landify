from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Report(BaseModel):
    """Báo cáo vi phạm"""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ xử lý"
        RESOLVED = "RESOLVED", "Đã giải quyết"
        REJECTED = "REJECTED", "Từ chối"

    class ItemType(models.TextChoices):
        LISTING = "listing", "Tin đăng"
        USER = "user", "Người dùng"
        POST = "post", "Bài đăng"
        COMMENT = "comment", "Bình luận"

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_reports", verbose_name="Người báo cáo"
    )
    description = models.TextField(verbose_name="Mô tả")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Trạng thái")

    reported_item_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    reported_item_id = models.PositiveIntegerField()
    reported_object = GenericForeignKey('reported_item_type', 'reported_item_id')

    class Meta:
        verbose_name = "Báo cáo"
        verbose_name_plural = "Các Báo cáo"

class ModerationAction(BaseModel):
    """
    Ghi lại một hành động xử lý cụ thể được thực hiện bởi một admin.
    Ví dụ: Gỡ tin đăng, Khóa tài khoản.
    """
    class ActionType(models.TextChoices):
        TAKE_DOWN_CONTENT = "TAKE_DOWN", "Gỡ nội dung"
        RESTORE_CONTENT = "RESTORE", "Khôi phục nội dung"
        WARN_USER = "WARN", "Cảnh cáo người dùng"
        BAN_USER = "BAN", "Khóa tài khoản người dùng"

    # Hành động này được kích hoạt bởi báo cáo nào (có thể là null nếu admin tự kiểm tra)
    report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="actions"
    )
    # Admin nào đã thực hiện hành động
    moderator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="moderation_actions"
    )
    # Loại hành động đã thực hiện
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    # Lý do/ghi chú của admin
    reason = models.TextField(help_text="Ghi chú của admin về lý do thực hiện hành động này.")

    # Đối tượng bị tác động (tin đăng, user, bài viết...)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('target_content_type', 'target_object_id')

    class Meta:
        verbose_name = "Hành động Xử lý"
        verbose_name_plural = "Các Hành động Xử lý"

class Protest(BaseModel):
    """Kháng nghị của người dùng khi tin đăng bị từ chối/gắn cờ"""

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "Đang xem xét"
        RESOLVED = "RESOLVED", "Đã giải quyết"
        REJECTED = "REJECTED", "Từ chối"

    action = models.OneToOneField(
        ModerationAction, on_delete=models.CASCADE, related_name='protest', verbose_name="Hành động bị kháng nghị"
    )
    # Người dùng gửi kháng nghị (thường là chủ của đối tượng bị xử lý)
    protester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="protests", verbose_name="Người kháng nghị"
    )
    reason = models.TextField(verbose_name="Lý do kháng nghị")

    # Thông tin xử lý kháng nghị
    admin_reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_protests",
        verbose_name="Admin xem xét kháng nghị"
    )
    resolution_note = models.TextField(blank=True, null=True, verbose_name="Ghi chú xử lý kháng nghị")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS,
                              verbose_name="Trạng thái")

    class Meta:
        verbose_name = "Kháng nghị"
        verbose_name_plural = "Các Kháng nghị"
