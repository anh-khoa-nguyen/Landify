from functools import partial
from django.db import transaction
from django.contrib import admin, messages
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from apps.common.tasks import notifications

from .models import User, UserProfile, Subscription


# ==============================================================================
# CORE USER ADMIN
# ==============================================================================
# Cấu hình trang quản trị cho model User chính và các Inline liên quan.

# Ghi chú: Hiển thị form để quản lý hồ sơ người dùng ngay trên trang User.
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Hồ sơ người dùng"
    fk_name = "user"
    # === MỚI: Bảo vệ các trường được điền tự động từ eKYC ===
    readonly_fields = (
        'nationality', 'home_town', 'address', 'id_card_number',
        'rating_score', 'rating_count', 'listing_count'
    )


# Ghi chú: Tùy chỉnh giao diện quản trị chính cho model User.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # --- CẬP NHẬT: Thêm các cột thông tin tổng quan ---
    list_display = (
        "username",
        "email",
        "get_full_name",
        "role",
        "listing_count",
        "property_count",
        "follower_count",
        "is_staff",
        "is_active",
        "is_identity_verified",
    )
    list_filter = ("role", "is_staff", "is_active", "is_identity_verified", "is_phone_verified")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("-date_joined",)
    inlines = (UserProfileInline,)
    readonly_fields = ('date_joined', 'last_login')  # MỚI: Bảo vệ các trường hệ thống

    # === MỚI: Thêm các actions quản trị hàng loạt ===
    actions = ['activate_users', 'deactivate_users', 'manually_verify_identity']

    def get_queryset(self, request):
        # Tối ưu hóa truy vấn bằng cách đếm sẵn các thông tin liên quan
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _listing_count=Count('listings', distinct=True),
            _property_count=Count('properties', distinct=True),
            _follower_count=Count('follower_set', distinct=True),
        )
        return queryset

    @admin.display(description="Tin đăng", ordering='_listing_count')
    def listing_count(self, obj):
        return obj._listing_count

    @admin.display(description="BĐS", ordering='_property_count')
    def property_count(self, obj):
        return obj._property_count

    @admin.display(description="Followers", ordering='_follower_count')
    def follower_count(self, obj):
        return obj._follower_count

    @admin.action(description=_('Kích hoạt các tài khoản đã chọn'))
    def activate_users(self, request, queryset):
        with transaction.atomic():
            for user in queryset:
                task_with_args = partial(
                    notifications.send_notification_to_user.delay,
                    user_id=user.id, category="account_status", title="Tài khoản của bạn đã được kích hoạt",
                    content="Chào mừng bạn quay trở lại! Tài khoản của bạn đã hoạt động bình thường."
                )
                transaction.on_commit(task_with_args)
            queryset.update(is_active=True)
        self.message_user(request, f"Đã kích hoạt và gửi thông báo cho {queryset.count()} tài khoản.", messages.SUCCESS)

    @admin.action(description=_('Vô hiệu hóa các tài khoản đã chọn'))
    def deactivate_users(self, request, queryset):
        queryset_to_update = queryset.exclude(pk=request.user.pk).exclude(is_superuser=True)
        with transaction.atomic():
            for user in queryset_to_update:
                task_with_args = partial(
                    notifications.send_notification_to_user.delay,
                    user_id=user.id, category="account_status", title="Tài khoản của bạn đã bị tạm khóa",
                    content="Tài khoản của bạn đã bị tạm khóa do vi phạm chính sách. Vui lòng liên hệ hỗ trợ để biết thêm chi tiết."
                )
                transaction.on_commit(task_with_args)
            updated_count = queryset_to_update.update(is_active=False)
        self.message_user(request, f"Đã vô hiệu hóa và gửi thông báo cho {updated_count} tài khoản.", messages.SUCCESS)

    @admin.action(description=_('Xác minh danh tính thủ công'))
    def manually_verify_identity(self, request, queryset):
        with transaction.atomic():
            for user in queryset:
                task_with_args = partial(
                    notifications.send_notification_to_user.delay,
                    user_id=user.id, category="verification", title="Chúc mừng, bạn đã xác minh danh tính thành công!",
                    content="Tài khoản của bạn đã được quản trị viên xác minh. Giờ đây bạn có thể sử dụng các tính năng nâng cao."
                )
                transaction.on_commit(task_with_args)
            updated_count = queryset.update(is_identity_verified=True)
        self.message_user(request, f"Đã xác minh danh tính và gửi thông báo cho {updated_count} tài khoản.",
                          messages.SUCCESS)

# ==============================================================================
# SUPPORTING MODEL ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các model phụ.

# Ghi chú: Tùy chỉnh giao diện quản trị cho các lượt theo dõi (Subscription).
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('follower_link', 'following_link', 'created_date')
    search_fields = ('follower__username', 'following__username')
    raw_id_fields = ('follower', 'following')
    list_select_related = ('follower', 'following')

    @admin.display(description="Người theo dõi", ordering='follower')
    def follower_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.follower.id])
        return format_html('<a href="{}">{}</a>', url, obj.follower.username)

    @admin.display(description="Đang theo dõi", ordering='following')
    def following_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.following.id])
        return format_html('<a href="{}">{}</a>', url, obj.following.username)