from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.common.tasks import notifications

from .models import ModerationAction, Protest, Report

# ==============================================================================
# CORE MODERATION ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các quy trình kiểm duyệt chính: Báo cáo và Kháng nghị.


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "reported_object_link", "short_description", "status", "created_date")
    list_filter = ("status", "reported_item_type")
    search_fields = ("reporter__username", "description")
    list_select_related = ("reporter",)
    raw_id_fields = ("reporter",)

    readonly_fields = (
        "reported_object_link",
        "created_date",
        "updated_date",
    )

    actions = ["mark_as_resolved", "mark_as_rejected", "take_down_and_resolve"]

    @admin.action(description=_("Đánh dấu đã giải quyết"))
    def mark_as_resolved(self, request, queryset):
        queryset.update(status=Report.Status.RESOLVED)

    @admin.action(description=_("Đánh dấu đã từ chối"))
    def mark_as_rejected(self, request, queryset):
        queryset.update(status=Report.Status.REJECTED)

    @admin.action(description=_("Gỡ nội dung & Đánh dấu đã giải quyết"))
    @transaction.atomic
    def take_down_and_resolve(self, request, queryset):
        updated_count = 0
        for report in queryset.filter(status=Report.Status.PENDING):
            target = report.reported_object
            if hasattr(target, "active"):
                # Gỡ nội dung
                target.active = False
                target.save(update_fields=["active"])

                # Tạo bản ghi hành động
                ModerationAction.objects.create(
                    report=report,
                    moderator=request.user,
                    action_type=ModerationAction.ActionType.TAKE_DOWN_CONTENT,
                    reason=f"Xử lý từ báo cáo #{report.id} qua admin action.",
                    target_object=target,
                )

                # Cập nhật trạng thái báo cáo
                report.status = Report.Status.RESOLVED
                report.save(update_fields=["status"])
                updated_count += 1

        if updated_count > 0:
            self.message_user(
                request, f"Đã gỡ nội dung và giải quyết thành công {updated_count} báo cáo.", messages.SUCCESS
            )

    @admin.display(description="Đối tượng bị báo cáo")
    def reported_object_link(self, obj: Report):
        if not obj.reported_object:
            return "Không có"

        target = obj.reported_object
        content_type = obj.reported_item_type
        admin_url = reverse(f"admin:{content_type.app_label}_{content_type.model}_change", args=(target.pk,))
        return format_html('<a href="{}">{} (ID: {})</a>', admin_url, str(target), target.pk)

    @admin.display(description="Mô tả")
    def short_description(self, obj: Report):
        return (obj.description[:75] + "...") if len(obj.description) > 75 else obj.description


# Ghi chú: Tùy chỉnh giao diện quản trị cho các Kháng nghị (Protest).
@admin.register(Protest)
class ProtestAdmin(admin.ModelAdmin):
    list_display = ("id", "get_protested_item", "protester", "status", "admin_reviewer", "created_date")
    list_filter = ("status",)
    search_fields = ("protester__username", "reason", "action__reason")

    readonly_fields = ("created_date", "updated_date")
    raw_id_fields = ("action", "protester", "admin_reviewer")
    list_select_related = ("protester", "admin_reviewer", "action__target_content_type")

    def save_model(self, request, obj, form, change):
        """
        Ghi đè để gửi thông báo cho người dùng khi trạng thái kháng nghị thay đổi.
        """
        if change and "status" in form.changed_data:
            # Chỉ gửi thông báo khi trạng thái chuyển sang các trạng thái cuối cùng
            if obj.status in [Protest.Status.RESOLVED, Protest.Status.REJECTED]:
                user_to_notify = obj.protester

                title = "Kháng nghị của bạn đã được xử lý"
                content = (
                    f"Kháng nghị của bạn cho hành động xử lý #{obj.action.id} đã có kết quả: "
                    f"'{obj.get_status_display()}'. Ghi chú của admin: {obj.resolution_note}"
                )

                # Tạo đối tượng liên quan để frontend có thể điều hướng
                related_item = {"type": "protest", "id": obj.id}

                # Gọi Celery task để gửi thông báo dưới nền
                transaction.on_commit(
                    lambda: notifications.send_notification_to_user.delay(
                        user_id=user_to_notify.id,
                        category="protest_resolution",
                        title=title,
                        content=content,
                        related_item=related_item,
                    )
                )

        # Đừng quên gọi phương thức save_model gốc để lưu đối tượng!
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """
        Làm cho các trường chính trở thành readonly sau khi đã tạo.
        'obj' is None trên trang 'add', và là object trên trang 'change'.
        """
        # Nếu đang ở trang "change" (obj tồn tại)
        if obj:
            # Thêm các trường này vào danh sách readonly
            return self.readonly_fields + ("action", "protester", "reason")
        # Nếu đang ở trang "add", chỉ dùng danh sách readonly_fields mặc định
        return self.readonly_fields

    @admin.display(description="Đối tượng bị kháng nghị")
    def get_protested_item(self, obj: Protest):
        if not obj.action or not obj.action.target_object:
            return "Không có"

        target = obj.action.target_object
        content_type = ContentType.objects.get_for_model(target)
        admin_url = reverse(f"admin:{content_type.app_label}_{content_type.model}_change", args=(target.pk,))
        return format_html('<a href="{}">{} (ID: {})</a>', admin_url, str(target), target.pk)


# ==============================================================================
# SUPPORTING MODEL ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các model phụ, đóng vai trò là log/bằng chứng.


# Ghi chú: Tùy chỉnh giao diện quản trị cho các Hành động xử lý (ModerationAction).
@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ("id", "moderator", "action_type", "target_object_link", "created_date")
    list_filter = ("action_type", "moderator")
    raw_id_fields = ("report", "moderator")
    readonly_fields = ("target_object_link",)
    list_select_related = ("moderator", "target_content_type")  # Tối ưu truy vấn

    @admin.display(description="Đối tượng bị tác động")
    def target_object_link(self, obj: ModerationAction):
        if not obj.target_object:
            return "Không có"

        target = obj.target_object
        content_type = obj.target_content_type
        admin_url = reverse(f"admin:{content_type.app_label}_{content_type.model}_change", args=(target.pk,))
        return format_html('<a href="{}">{} (ID: {})</a>', admin_url, str(target), target.pk)
