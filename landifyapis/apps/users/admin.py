from django.contrib import admin
from .models import User, UserProfile, Subscription

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Hồ sơ người dùng"
    fk_name = "user"

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "is_active",
        "is_identity_verified",
    )
    list_filter = ("role", "is_staff", "is_active", "is_identity_verified", "is_phone_verified")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("-date_joined",)
    inlines = (UserProfileInline,)

admin.site.register(Subscription)
# admin.site.register(Cooperation)