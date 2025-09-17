from django.db import models
from django.utils import timezone

from django.contrib.gis.db import models as gis_models
from apps.common.models import BaseModel
from apps.properties.models import Property
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.users.models import User

class Appointment(BaseModel):
    """Lịch hẹn xem nhà cho một TIN ĐĂNG cụ thể."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ xác nhận"
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        COMPLETED = "COMPLETED", "Đã hoàn thành"
        CANCELLED = "CANCELLED", "Đã hủy"

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="appointments", verbose_name="Tin đăng"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments", verbose_name="Người hẹn")
    appointment_date = models.DateTimeField(verbose_name="Thời gian hẹn")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Trạng thái")

    class Meta:
        verbose_name = "Lịch hẹn"
        verbose_name_plural = "Các Lịch hẹn"

class Review(BaseModel):
    """Đánh giá cho một bất động sản"""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="reviews", verbose_name="Bất động sản"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews", verbose_name="Người đánh giá")
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Điểm")
    comment = models.TextField(verbose_name="Bình luận")

    point = gis_models.PointField(srid=4326, null=True, blank=True, verbose_name="Vị trí lúc đánh giá")

    class Meta:
        unique_together = ("user", "property")
        verbose_name = "Đánh giá"
        verbose_name_plural = "Các Đánh giá"

class Wishlist(BaseModel):
    """Danh sách yêu thích của người dùng"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist", verbose_name="Người dùng")
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="wishlisted_by", verbose_name="Tin đăng"
    )

    class Meta:
        unique_together = ("user", "listing")
        verbose_name = "Danh sách yêu thích"
        verbose_name_plural = "Các Danh sách yêu thích"

#======================================================================

class Chat(BaseModel):
    # Định nghĩa các loại chat có thể có
    class ChatType(models.TextChoices):
        PRIVATE = 'PRIVATE', 'Private'
        GROUP = 'GROUP', 'Group'

    # Trường này sẽ cho biết đây là chat riêng hay chat nhóm
    chat_type = models.CharField(
        max_length=10,
        choices=ChatType.choices,
        default=ChatType.PRIVATE
    )

    # Quay lại dùng ManyToManyField, nó đủ linh hoạt cho cả 2 trường hợp
    # Chat riêng sẽ có 2 participants, chat nhóm sẽ có > 2
    participants = models.ManyToManyField(
        User,
        related_name="chats",
        help_text="Những người tham gia cuộc trò chuyện."
    )

    # Tên của phòng chat, chỉ bắt buộc cho chat nhóm
    name = models.CharField(max_length=100, blank=True, null=True)

    # Vẫn giữ lại listing, nhưng cho phép null
    # vì có thể có những cuộc chat không liên quan đến tin đăng
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL, # Dùng SET_NULL để không mất chat khi tin đăng bị xóa
        related_name="chats",
        blank=True,
        null=True
    )

    last_message_timestamp = models.DateTimeField(
        default=timezone.now,  # Đặt giá trị mặc định là thời gian tạo chat
        db_index=True,  # Thêm index để tăng tốc độ sắp xếp
        verbose_name="Thời gian tin nhắn cuối"
    )

    def __str__(self):
        if self.chat_type == self.ChatType.GROUP and self.name:
            return f"Group Chat: {self.name}"
        elif self.chat_type == self.ChatType.PRIVATE:
            # Lấy 2 người đầu tiên để hiển thị, cần tối ưu hơn trong thực tế
            users = self.participants.all()[:2]
            user_names = " & ".join([user.username for user in users])
            return f"Private Chat: {user_names}"
        return f"Chat ID: {self.id}"


class Message(BaseModel):
    # === CÁC LOẠI TIN NHẮN CÓ THỂ CÓ ===
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Tin nhắn văn bản'
        IMAGE = 'IMAGE', 'Hình ảnh'
        FILE = 'FILE', 'Tệp đính kèm'
        SYSTEM = 'SYSTEM', 'Thông báo hệ thống'  # Ví dụ: "A đã tham gia cuộc trò chuyện"
        LISTING_LINK = 'LISTING_LINK', 'Liên kết tin đăng'
        INTERACTIVE_CARD = 'INTERACTIVE_CARD', 'Thẻ tương tác'

    # === CÁC TRƯỜNG CỐT LÕI ===

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Cuộc trò chuyện"
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,  # Khi người dùng bị xóa, tin nhắn của họ cũng bị xóa
        related_name='sent_messages',
        verbose_name="Người gửi"
    )

    # Nội dung chính của tin nhắn (văn bản, hoặc mô tả cho file/ảnh)
    content = models.TextField(
        blank=True,  # Cho phép tin nhắn chỉ có file mà không có text
        verbose_name="Nội dung"
    )

    message_type = models.CharField(
        max_length=25,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name="Loại tin nhắn"
    )

    attachment_url = models.URLField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="URL tệp đính kèm"
    )

    read_by = models.ManyToManyField(
        User,
        related_name='read_messages',
        blank=True,
        verbose_name="Đã đọc bởi"
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True, # Cho phép null vì tin nhắn TEXT không có đối tượng liên kết
        blank=True
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    # 3. Trường ảo để truy cập đối tượng một cách tiện lợi
    linked_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['created_date']
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Các Tin nhắn"

    def __str__(self):
        return f"Tin nhắn từ {self.sender.username} trong chat {self.chat.id}"

#===============================================================================
class Cooperation(BaseModel):
    """
    Model quản lý một yêu cầu và trạng thái hợp tác môi giới
    giữa một người dùng (agent) và một tin đăng (listing).
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Đang chờ"
        ACCEPTED = "ACCEPTED", "Đã chấp nhận"
        REJECTED = "REJECTED", "Đã từ chối"
        SOLD = "SOLD", "BĐS đã bán"  # Trạng thái kết thúc khi BĐS được bán bởi người khác
        CANCELLED = "CANCELLED", "Đã hủy"  # Trạng thái kết thúc khi một trong hai bên hủy hợp tác

    listing = models.ForeignKey(
        'listings.Listing',
        on_delete=models.CASCADE,
        related_name="cooperations",
        verbose_name="Tin đăng"
    )
    # Người yêu cầu hợp tác (môi giới)
    agent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_cooperations",
        verbose_name="Môi giới yêu cầu"
    )
    # Chủ tin đăng (người nhận yêu cầu)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_cooperations",
        verbose_name="Chủ tin đăng"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Trạng thái"
    )

    # Ghi chú cho các hành động
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Lý do từ chối")
    cancellation_reason = models.TextField(blank=True, null=True, verbose_name="Lý do hủy")

    class Meta:
        verbose_name = "Hợp tác môi giới"
        verbose_name_plural = "Các Hợp tác môi giới"
        # Đảm bảo một môi giới chỉ có thể gửi một yêu cầu cho một tin đăng
        unique_together = ('listing', 'agent')

    def __str__(self):
        return f"Yêu cầu hợp tác từ {self.agent.username} cho tin '{self.listing.title}'"