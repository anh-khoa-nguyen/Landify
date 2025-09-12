from django.contrib import admin
from .models import Report, Protest

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

@admin.register(Protest)
class ProtestAdmin(admin.ModelAdmin):
    list_display = ("listing", "protester", "status", "admin", "created_date")
    list_filter = ("status",)
    search_fields = ("listing__title", "protester__username", "reason")
    readonly_fields = ("listing", "protester", "reason", "created_date", "updated_date")
    raw_id_fields = ("listing", "protester", "admin")