from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.forms.widgets import OSMWidget
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Direction, LegalStatus, Location, Property, PropertyFeature, PropertyMedia, PropertyType

# ==============================================================================
# CORE PROPERTY ADMIN
# ==============================================================================
# Cấu hình trang quản trị cho model Property chính và các Inline liên quan.


# Ghi chú: Hiển thị form để upload/quản lý media (ảnh/video) ngay trên trang Property.
class PropertyMediaInline(admin.TabularInline):
    model = PropertyMedia
    extra = 1
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" width="150" />', obj.url.url)
        return "Không có ảnh"

    image_preview.short_description = "Xem trước"


# Ghi chú: Tùy chỉnh giao diện quản trị chính cho model Property.
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):  # <-- THAY ĐỔI: Quay lại ModelAdmin thông thường
    list_display = (
        "id",
        "owner_link",
        "property_type",
        "display_location",
        "area",
        "media_count",
        "listing_count",
        "active",
    )
    list_filter = (
        "active",
        "property_type",
        "legal_status",
        "location__ward__parent_code__parent_code",
    )
    search_fields = (
        "owner__username",
        "location__street",
        "location__ward__name",
        "location__ward__parent_code__name",
    )

    # === THAY ĐỔI QUAN TRỌNG NHẤT TẠI ĐÂY ===
    # Áp dụng raw_id_fields cho trường 'location' trực tiếp.
    raw_id_fields = ("owner", "location")
    # =======================================

    inlines = [PropertyMediaInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _media_count=Count("media", distinct=True), _listing_count=Count("listings", distinct=True)
        )
        return queryset

    # ... (các hàm display link và count giữ nguyên) ...
    @admin.display(description="Media", ordering="_media_count")
    def media_count(self, obj):
        return obj._media_count

    @admin.display(description="Tin đăng", ordering="_listing_count")
    def listing_count(self, obj):
        return obj._listing_count

    @admin.display(description="Chủ sở hữu", ordering="owner")
    def owner_link(self, obj):
        if obj.owner:
            url = reverse("admin:users_user_change", args=[obj.owner.id])
            return format_html('<a href="{}">{}</a>', url, obj.owner.username)
        return "-"

    @admin.display(description="Địa chỉ")
    def display_location(self, obj):
        return str(obj.location) if obj.location else "Chưa có địa chỉ"


# ==============================================================================
# SUPPORTING MODEL ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các model phụ.


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active")
    search_fields = ("name", "code")


# Ghi chú: Tùy chỉnh giao diện quản trị cho Location, tích hợp bản đồ.
@admin.register(Location)
class LocationAdmin(GISModelAdmin):  # <-- Giữ nguyên GISModelAdmin ở đây là đúng
    list_display = ("id", "street", "ward")  # Thêm ID để dễ chọn trong popup
    search_fields = ("street", "ward__name", "ward__parent_code__name")  # Thêm tìm kiếm
    raw_id_fields = ("ward",)
    gis_widget_kwargs = {
        "attrs": {
            "default_lat": 10.7769,
            "default_lon": 106.7009,
            "default_zoom": 12,
            "map_width": 800,
            "map_height": 500,
        }
    }


admin.site.register(Direction)
admin.site.register(LegalStatus)
admin.site.register(PropertyFeature)
