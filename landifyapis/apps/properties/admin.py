from django.contrib import admin
from django.utils.html import format_html
from .models import Property, PropertyMedia, PropertyType, Direction, LegalStatus, Location, PropertyFeature

class PropertyMediaInline(admin.TabularInline):
    model = PropertyMedia
    extra = 1  # Hiển thị sẵn 1 dòng trống để thêm mới
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" width="150" />', obj.url.url)
        return "Không có ảnh"

    image_preview.short_description = "Xem trước"

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "property_type", "display_location", "area", "active")
    list_filter = ("active", "property_type", "legal_status")
    search_fields = ("owner__username", "location__street",)
    raw_id_fields = ("owner", "location")  # Tối ưu cho ForeignKey có nhiều lựa chọn
    inlines = (PropertyMediaInline,)  # <<< Nhúng Media vào đây

    @admin.display(description="Địa chỉ")
    def display_location(self, obj):
        return str(obj.location) if obj.location else "Chưa có địa chỉ"

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active")
    search_fields = ("name", "code")

admin.site.register(Direction)
admin.site.register(LegalStatus)
admin.site.register(Location)
admin.site.register(PropertyFeature)
