from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User

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

    # Sử dụng Generic Foreign Key để trỏ đến nhiều loại đối tượng
    reported_item_id = models.PositiveIntegerField(verbose_name="ID đối tượng bị báo cáo")
    reported_item_type = models.CharField(
        max_length=20, choices=ItemType.choices, verbose_name="Loại đối tượng bị báo cáo"
    )

    class Meta:
        verbose_name = "Báo cáo"
        verbose_name_plural = "Các Báo cáo"


class Protest(BaseModel):
    """Kháng nghị của người dùng khi tin đăng bị từ chối/gắn cờ"""

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "Đang xem xét"
        RESOLVED = "RESOLVED", "Đã giải quyết"
        REJECTED = "REJECTED", "Từ chối"

    # listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='protests', verbose_name="Tin đăng")
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="protests", verbose_name="Tin đăng"
    )
    protester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="protests", verbose_name="Người kháng nghị"
    )
    reason = models.TextField(verbose_name="Lý do kháng nghị")
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_protests",
        verbose_name="Admin xử lý",
    )
    resolution_note = models.TextField(blank=True, null=True, verbose_name="Ghi chú xử lý")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, verbose_name="Trạng thái"
    )

    class Meta:
        verbose_name = "Kháng nghị"
        verbose_name_plural = "Các Kháng nghị"
