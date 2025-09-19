from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

from .models import (
    Listing, ListingPropertyFeatureValue, ListingType, UnitPrice,
    VipType, ListingVip, ListingCategory, PromotionRule, UserPromotion
)
from apps.properties.models import PropertyFeature # <-- THÊM DÒNG NÀY

# ==============================================================================
# CORE LISTING ADMIN
# ==============================================================================
# Cấu hình trang quản trị cho model Listing chính và các Inline liên quan.

# Ghi chú: Hiển thị form để chỉnh sửa các đặc điểm (features) ngay trên trang Listing.
class ListingPropertyFeatureValueInline(admin.TabularInline):
    model = ListingPropertyFeatureValue
    extra = 1
    readonly_fields = ("display_value",)
    fields = ("feature", "value", "display_value")
    #raw_id_fields = ('feature',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "feature":
            parent_listing_id = request.resolver_match.kwargs.get('object_id')
            if parent_listing_id:
                try:
                    listing = Listing.objects.get(pk=parent_listing_id)

                    # Tìm ListingCategory dựa trên listing_type và property_type của tin đăng
                    # Dùng select_related để tối ưu
                    category = ListingCategory.objects.select_related(
                        'listing_type', 'property_type'
                    ).filter(
                        listing_type=listing.listing_type,
                        property_type=listing.property.property_type
                    ).first()

                    if category:
                        # Lấy danh sách các feature được phép từ trường ManyToMany
                        # Dùng prefetch_related nếu bạn cần truy cập các trường khác của feature
                        allowed_features = category.applicable_features.all()
                        kwargs["queryset"] = allowed_features
                    else:
                        # Nếu không tìm thấy category, trả về một queryset rỗng
                        kwargs["queryset"] = PropertyFeature.objects.none()

                except Listing.DoesNotExist:
                    pass
            else:
                # Trên trang "Add", không có object_id, trả về rỗng để buộc người dùng
                # phải lưu tin đăng trước khi có thể thêm feature.
                # Điều này đảm bảo logic luôn đúng.
                kwargs["queryset"] = PropertyFeature.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Ghi chú: Hiển thị form để quản lý trạng thái VIP ngay trên trang Listing.
class ListingVipInline(admin.StackedInline):
    model = ListingVip
    can_delete = False
    verbose_name_plural = 'Trạng thái VIP'
    # Các trường có thể chỉnh sửa
    fields = ('vip_type', 'end_date')
    # Hiển thị các trường chỉ đọc để admin tham khảo
    readonly_fields = ('is_active',)

# Ghi chú: Tùy chỉnh giao diện quản trị chính cho model Listing.
@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user_link",
        "property_link",
        "listing_type",
        "status",
        "spam_check_status",
        "scam_score",
        "created_date",
        "active"
    )
    list_filter = (
        "active",
        "status",
        "spam_check_status",
        "listing_type",
        ("created_date", admin.DateFieldListFilter),
    )
    search_fields = ("title", "user__username", "property__location__street")
    readonly_fields = (
        "created_date",
        "updated_date",
        "scam_score",
        "scam_detector_version"
    )
    raw_id_fields = ("user", "property")
    inlines = [
        ListingPropertyFeatureValueInline,
        ListingVipInline
    ]

    actions = ['make_active', 'make_inactive', 'mark_as_clean']

    @admin.action(description=_('Kích hoạt các tin đăng đã chọn'))
    def make_active(self, request, queryset):
        queryset.update(active=True)

    @admin.action(description=_('Vô hiệu hóa các tin đăng đã chọn'))
    def make_inactive(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description=_('Đánh dấu "Trong sạch" cho các tin đã chọn'))
    def mark_as_clean(self, request, queryset):
        queryset.update(spam_check_status=Listing.SpamCheckStatus.CLEAN)

    # === Các hàm tạo link điều hướng ===
    @admin.display(description="Người đăng", ordering='user')
    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:users_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"

    @admin.display(description="Bất động sản", ordering='property')
    def property_link(self, obj):
        if obj.property:
            url = reverse("admin:properties_property_change", args=[obj.property.id])
            return format_html('<a href="{}">ID: {}</a>', url, obj.property.id)
        return "-"

# ==============================================================================
# SUPPORTING MODEL ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các model phụ, đóng vai trò là các bảng
# cài đặt hoặc tùy chọn cho Listing.

@admin.register(ListingType)
class ListingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'active')
    filter_horizontal = ('applicable_unit_prices',)

@admin.register(ListingCategory)
class ListingCategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'listing_type', 'property_type', 'feature_count')
    list_filter = ('listing_type', 'property_type')
    search_fields = ('listing_type__name', 'property_type__name')
    list_select_related = ('listing_type', 'property_type')

    # Sử dụng widget filter_horizontal cho trường ManyToMany
    filter_horizontal = ('applicable_features',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_feature_count=Count('applicable_features'))
        return queryset

    @admin.display(description="Tên danh mục")
    def display_name(self, obj):
        # Sử dụng property có sẵn trong model
        return obj.display_name

    @admin.display(description="Số features", ordering='_feature_count')
    def feature_count(self, obj):
        return obj._feature_count


# Ghi chú: Quản lý các quy tắc/chương trình khuyến mãi gốc.
@admin.register(PromotionRule)
class PromotionRuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'promo_type', 'trigger_event', 'active')
    list_filter = ('promo_type', 'trigger_event', 'active')
    search_fields = ('title', 'description')

    # Dùng filter_horizontal cho việc chọn các gói VIP được áp dụng
    filter_horizontal = ('applicable_vip_types',)

    # === SỬA LỖI VÀ CẢI TIẾN BẰNG FIELDSETS ===
    fieldsets = (
        ('Thông tin chung', {
            'fields': ('title', 'description', 'active')
        }),
        ('Loại hình và Kích hoạt', {
            'fields': ('promo_type', 'trigger_event')
        }),
        ('Giá trị Khuyến mãi', {
            'description': "Điền vào một trong các trường dưới đây, tùy thuộc vào 'Loại hình' đã chọn ở trên.",
            'fields': ('free_listing_days', 'discount_percentage', 'applicable_vip_types')
        }),
        ('Thời hạn Hiệu lực', {
            'description': "Nếu kích hoạt 'Khi đăng ký tài khoản', hãy điền 'Thời hạn hiệu lực'.",
            'fields': ('validity_duration',)
        }),
    )


# Ghi chú: Quản lý các mã khuyến mãi đã được cấp cho từng người dùng.
@admin.register(UserPromotion)
class UserPromotionAdmin(admin.ModelAdmin):
    list_display = ('code', 'user_link', 'rule_link', 'status', 'expiry_date', 'used_on_listing_link')
    list_filter = ('status', 'rule__promo_type')
    search_fields = ('code', 'user__username', 'rule__title')
    raw_id_fields = ('user', 'rule', 'used_on_listing')
    list_select_related = ('user', 'rule', 'used_on_listing')

    # Cho phép admin tạo mã KM thủ công
    fields = ('user', 'rule', 'code', 'expiry_date', 'status')
    # Các trường này chỉ để xem, không cho sửa
    readonly_fields = ('used_at', 'used_on_listing_link')

    # Ghi đè để thêm link vào trường used_on_listing
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.used_on_listing:
            # Nếu đã sử dụng, hiển thị thêm thông tin chỉ đọc
            fieldsets = list(fieldsets)
            fieldsets.append(
                ('Thông tin sử dụng (Chỉ đọc)', {
                    'fields': ('used_at', 'used_on_listing_link'),
                })
            )
        return fieldsets

    @admin.display(description="Người dùng", ordering='user')
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    @admin.display(description="Quy tắc KM", ordering='rule')
    def rule_link(self, obj):
        url = reverse("admin:listings_promotionrule_change", args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.title)

    @admin.display(description="Sử dụng trên tin", ordering='used_on_listing')
    def used_on_listing_link(self, obj):
        if obj.used_on_listing:
            url = reverse("admin:listings_listing_change", args=[obj.used_on_listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.used_on_listing.title)
        return "-"

@admin.register(VipType)
class VipTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_per_day", "sort_priority", "active")
    search_fields = ("name", "code")

admin.site.register(UnitPrice)