from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType
from .models import Report, Protest, ModerationAction


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "reported_item_type", "reported_item_id", "status", "created_date")
    list_filter = ("status", "reported_item_type")
    search_fields = ("reporter__username", "description")
    readonly_fields = (
        "reporter",
        "reported_item_type",
        "reported_item_id",
        "description",
        "created_date",
        "updated_date",
    )
    actions = ["mark_as_resolved", "mark_as_rejected"]

    @admin.action(description="Đánh dấu các báo cáo đã được giải quyết")
    def mark_as_resolved(self, request, queryset):
        queryset.update(status=Report.Status.RESOLVED)

    @admin.action(description="Đánh dấu các báo cáo đã bị từ chối")
    def mark_as_rejected(self, request, queryset):
        queryset.update(status=Report.Status.REJECTED)

# === ĐĂNG KÝ MODEL MỚI: ModerationAction ===
@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'moderator', 'action_type', 'reason', 'created_date')
    list_filter = ('action_type', 'moderator')
    raw_id_fields = ('report', 'moderator')
    readonly_fields = ('target_object',)


@admin.register(Protest)
class ProtestAdmin(admin.ModelAdmin):
    # --- THAY ĐỔI 1: Cập nhật list_display ---
    list_display = ("get_protested_item", "protester", "status", "admin_reviewer", "created_date")
    list_filter = ("status",)

    # --- THAY ĐỔI 2: Cập nhật search_fields ---
    # Không thể tìm kiếm trực tiếp qua GenericForeignKey, ta tìm qua các trường liên quan
    search_fields = ("protester__username", "reason", "action__reason")

    # --- THAY ĐỔI 3: Cập nhật readonly_fields ---
    readonly_fields = ("action", "protester", "reason", "created_date", "updated_date")

    # --- THAY ĐỔI 4: Cập nhật raw_id_fields ---
    raw_id_fields = ("action", "protester", "admin_reviewer")

    # --- THAY ĐỔI 5: Thêm một phương thức tùy chỉnh để hiển thị thông tin đẹp hơn ---
    @admin.display(description="Đối tượng bị kháng nghị")
    def get_protested_item(self, obj: Protest):
        """
        Hiển thị một đường link đến trang admin của đối tượng bị xử lý (listing, user, post...).
        """
        if not obj.action or not obj.action.target_object:
            return "Không có"

        target = obj.action.target_object
        # Lấy content type của đối tượng (vd: 'listing', 'user')
        content_type = ContentType.objects.get_for_model(target)

        # Tạo URL đến trang admin của đối tượng đó
        admin_url = reverse(
            f"admin:{content_type.app_label}_{content_type.model}_change",
            args=(target.pk,)
        )

        # Trả về một thẻ HTML có link
        return format_html('<a href="{}">{} (ID: {})</a>', admin_url, str(target), target.pk)