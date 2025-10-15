from functools import partial

from django.contrib import admin, messages
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.forms.widgets import OSMWidget
from django.db import transaction
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.common.tasks import notifications

from .models import Appointment, Chat, Cooperation, Message, Review, Wishlist

# ==============================================================================
# CORE INTERACTION ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho các model tương tác chính của người dùng.


# Ghi chú: Tùy chỉnh giao diện quản trị cho Đánh giá (Review).
@admin.register(Review)
class ReviewAdmin(GISModelAdmin):
    list_display = ("property_link", "user_link", "rating", "short_comment", "point", "created_date")
    list_filter = ("rating", "created_date")
    search_fields = ("user__username", "property__id", "comment")  # MỚI: Thêm tìm kiếm
    raw_id_fields = ("property", "user")
    list_select_related = ("property", "user")  # MỚI: Tối ưu truy vấn

    gis_widget_kwargs = {
        "attrs": {
            "default_lat": 10.7769,
            "default_lon": 106.7009,
            "default_zoom": 12,
            "map_width": 800,
            "map_height": 500,
        }
    }

    @admin.display(description="Bất động sản", ordering="property")
    def property_link(self, obj):
        url = reverse("admin:properties_property_change", args=[obj.property.id])
        return format_html('<a href="{}">BĐS ID: {}</a>', url, obj.property.id)

    @admin.display(description="Người đánh giá", ordering="user")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    @admin.display(description="Bình luận")
    def short_comment(self, obj: Review):
        return (obj.comment[:75] + "...") if len(obj.comment) > 75 else obj.comment


# Ghi chú: Tùy chỉnh giao diện quản trị cho Danh sách yêu thích (Wishlist).
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user_link", "listing_link", "created_date")
    search_fields = ("user__username", "listing__title")  # MỚI: Thêm tìm kiếm
    raw_id_fields = ("user", "listing")
    list_select_related = ("user", "listing")  # MỚI: Tối ưu truy vấn

    @admin.display(description="Người dùng", ordering="user")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    @admin.display(description="Tin đăng", ordering="listing")
    def listing_link(self, obj):
        url = reverse("admin:listings_listing_change", args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)


# Ghi chú: Tùy chỉnh giao diện quản trị cho Lịch hẹn (Appointment).
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("listing_link", "user_link", "listing_owner_link", "appointment_date", "status")
    list_filter = ("status", "appointment_date")
    search_fields = ("user__username", "listing__title", "listing__user__username")  # MỚI: Thêm tìm kiếm
    raw_id_fields = ("listing", "user")
    list_select_related = ("listing__user", "user")  # MỚI: Tối ưu truy vấn
    actions = ["confirm_appointments", "cancel_appointments"]  # MỚI: Thêm actions

    @admin.action(description=_("Xác nhận các lịch hẹn đã chọn"))
    def confirm_appointments(self, request, queryset):
        appointments_to_confirm = queryset.filter(status=Appointment.Status.PENDING)

        with transaction.atomic():
            updated_count = appointments_to_confirm.update(status=Appointment.Status.CONFIRMED)

            updated_ids = appointments_to_confirm.values_list("id", flat=True)
            appointments_for_notif = Appointment.objects.filter(id__in=updated_ids)

            for app in appointments_for_notif:
                title = "Lịch hẹn của bạn đã được xác nhận"
                content = f"Lịch hẹn xem tin '{app.listing.title}' vào lúc {app.appointment_date.strftime('%H:%M %d/%m/%Y')} đã được chủ tin đăng xác nhận."
                related_item = {"type": "appointment", "id": app.id}

                task_with_args = partial(
                    notifications.send_notification_to_user.delay,
                    user_id=app.user.id,
                    category="appointment_update",
                    title=title,
                    content=content,
                    related_item=related_item,
                )
                transaction.on_commit(task_with_args)

        self.message_user(request, f"Đã xác nhận và gửi thông báo cho {updated_count} lịch hẹn.", messages.SUCCESS)

    @admin.action(description=_("Hủy các lịch hẹn đã chọn"))
    def cancel_appointments(self, request, queryset):
        appointments_to_cancel = queryset.exclude(
            status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]
        )

        with transaction.atomic():
            updated_count = appointments_to_cancel.update(status=Appointment.Status.CANCELLED)

            updated_ids = appointments_to_cancel.values_list("id", flat=True)
            appointments_for_notif = Appointment.objects.filter(id__in=updated_ids)

            for app in appointments_for_notif:
                title = "Lịch hẹn của bạn đã bị hủy"
                content = f"Rất tiếc, lịch hẹn xem tin '{app.listing.title}' đã bị hủy bởi quản trị viên."
                related_item = {"type": "appointment", "id": app.id}

                task_with_args = partial(
                    notifications.send_notification_to_user.delay,
                    user_id=app.user.id,
                    category="appointment_update",
                    title=title,
                    content=content,
                    related_item=related_item,
                )
                transaction.on_commit(task_with_args)

        self.message_user(request, f"Đã hủy và gửi thông báo cho {updated_count} lịch hẹn.", messages.SUCCESS)

    @admin.display(description="Tin đăng", ordering="listing")
    def listing_link(self, obj):
        url = reverse("admin:listings_listing_change", args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    @admin.display(description="Người hẹn", ordering="user")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    @admin.display(description="Chủ tin đăng", ordering="listing__user")
    def listing_owner_link(self, obj):
        owner = obj.listing.user
        url = reverse("admin:users_user_change", args=[owner.id])
        return format_html('<a href="{}">{}</a>', url, owner.username)


@admin.register(Cooperation)
class CooperationAdmin(admin.ModelAdmin):
    list_display = ("id", "listing_link", "agent_link", "owner_link", "status", "created_date")
    list_filter = ("status", "created_date")
    search_fields = ("agent__username", "owner__username", "listing__title")
    raw_id_fields = ("listing", "agent", "owner")
    list_select_related = ("listing", "agent", "owner")

    # Cho phép admin chỉnh sửa các trường này
    fields = ("listing", "agent", "owner", "status", "rejection_reason", "cancellation_reason")
    # Các trường hệ thống sẽ là readonly
    readonly_fields = ("created_date", "updated_date")

    @admin.display(description="Tin đăng", ordering="listing")
    def listing_link(self, obj):
        url = reverse("admin:listings_listing_change", args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    @admin.display(description="Môi giới yêu cầu", ordering="agent")
    def agent_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.agent.id])
        return format_html('<a href="{}">{}</a>', url, obj.agent.username)

    @admin.display(description="Chủ tin đăng", ordering="owner")
    def owner_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.owner.id])
        return format_html('<a href="{}">{}</a>', url, obj.owner.username)


# ==============================================================================
# CHAT & MESSAGING ADMINS
# ==============================================================================
# Cấu hình trang quản trị cho hệ thống trò chuyện.


# Ghi chú: Inline để hiển thị danh sách tin nhắn ngay trên trang chi tiết Chat.
class MessageInline(admin.TabularInline):
    model = Message
    extra = 0  # Không hiển thị dòng trống để thêm mới
    readonly_fields = ("sender", "content", "message_type", "linked_object", "created_date")
    fields = ("sender", "content", "message_type", "linked_object", "created_date")

    def has_add_permission(self, request, obj=None):
        # Admin không nên có quyền gửi tin nhắn từ đây
        return False

    def has_delete_permission(self, request, obj=None):
        # Cho phép xóa tin nhắn vi phạm nếu cần
        return True


# Ghi chú: Tùy chỉnh giao diện quản trị cho các Cuộc trò chuyện (Chat).
@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_type", "listing_link", "participant_list", "message_count", "last_message_timestamp")
    list_filter = ("chat_type", "created_date")
    search_fields = ("participants__username", "listing__title", "id")
    raw_id_fields = ("participants", "listing")
    inlines = [MessageInline]
    list_select_related = ("listing",)
    list_prefetch_related = ("participants",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_message_count=Count("messages"))
        return queryset

    @admin.display(description="Tin nhắn", ordering="_message_count")
    def message_count(self, obj):
        return obj._message_count

    @admin.display(description="Những người tham gia")
    def participant_list(self, obj):
        # Hiển thị 3 người đầu tiên để tránh làm vỡ layout
        participants = obj.participants.all()[:3]
        return ", ".join([p.username for p in participants])

    @admin.display(description="Tin đăng liên quan", ordering="listing")
    def listing_link(self, obj):
        if obj.listing:
            url = reverse("admin:listings_listing_change", args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "N/A"


# Ghi chú: Tùy chỉnh giao diện quản trị cho các Tin nhắn (Message).
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_link", "sender", "short_content", "message_type", "created_date")
    list_filter = ("message_type", "created_date")
    search_fields = ("sender__username", "content", "chat__id")
    raw_id_fields = ("chat", "sender")
    list_select_related = ("chat", "sender")

    @admin.display(description="Nội dung")
    def short_content(self, obj: Message):
        return (obj.content[:75] + "...") if len(obj.content) > 75 else obj.content

    @admin.display(description="Cuộc trò chuyện", ordering="chat")
    def chat_link(self, obj):
        url = reverse("admin:interactions_chat_change", args=[obj.chat.id])
        return format_html('<a href="{}">Chat ID: {}</a>', url, obj.chat.id)

    def has_add_permission(self, request):
        return False  # Admin không nên tạo tin nhắn mới từ đây
