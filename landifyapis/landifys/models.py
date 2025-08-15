from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.utils import timezone
from django.contrib.auth.hashers import is_password_usable
from vi_address.models import City, District, Ward

#=================== BASE & USER ==========================

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'OTHER', 'Other'

    role = models.CharField(max_length=10, choices=Role.choices, default='user')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.OTHER)
    phone_number = models.CharField(max_length=15, null=True, blank=True, unique=True)
    is_phone_verified = models.BooleanField(default=False);
    is_id_card_verified = models.BooleanField(default=False);
    id_card_data = models.JSONField(null=True, blank=True)
    avatar = CloudinaryField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256$') and is_password_usable(self.password):
            self.set_password(self.password)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id']

# =================== PROPERTY & RELATED MODELS ==========================

class PropertyType(BaseModel):
    """Loại bất động sản (VD: Căn hộ, Nhà phố, Đất nền)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Direction(BaseModel):
    """Hướng nhà (VD: Đông, Tây, Nam, Bắc)"""
    name = models.CharField(max_length=50, unique=True, help_text="Tên hướng, ví dụ: Đông, Tây Nam") #Tên hướng
    element = models.CharField(max_length=20, help_text="Hành tương ứng, ví dụ: Mộc, Kim, Hỏa") #Hành tương ứng

    def __str__(self):
        return self.name

class Utility(BaseModel):
    """Tiện ích (VD: Hồ bơi, Phòng gym, Gần trường học)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Location(BaseModel):
    """Lưu địa chỉ có cấu trúc của bất động sản"""
    street = models.CharField(max_length=255)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, verbose_name="Phường/Xã")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, verbose_name="Quận/Huyện")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, verbose_name="Tỉnh/Thành phố")
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    def __str__(self):
        full_address = f"{self.street}, {self.ward}, {self.district}, {self.city}"
        return full_address

    class Meta:
        verbose_name = "Địa điểm"
        verbose_name_plural = "Các Địa điểm"

class Property(BaseModel):
    """
    Model Bất động sản - Chỉ chứa các thông tin vật lý, cố định của tài sản.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_properties')
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True)
    location = models.OneToOneField(Location, on_delete=models.SET_NULL, null=True)
    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.FloatField()
    has_legal_docs = models.BooleanField(default=False)
    floor_num = models.IntegerField(null=True, blank=True)
    bedroom_count = models.PositiveIntegerField(default=1)
    bathroom_count = models.PositiveIntegerField(default=1)
    utilities = models.ManyToManyField(Utility, through='PropertyUtility', blank=True)

    def __str__(self):
        return f"Property ID {self.id} at {self.location}"

class PropertyUtility(models.Model):
    """Bảng trung gian cho Property và Utility."""
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    utility = models.ForeignKey(Utility, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('property', 'utility')

class ListingType(BaseModel):
    """Loại tin đăng: Bán, Cho thuê."""
    name = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.name

class Listing(BaseModel):
    """
    Model Tin đăng - Chứa thông tin của một lần chào bán/cho thuê.
    Đây là trung tâm của các hoạt động giao dịch.
    """
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Đang đăng'
        PENDING = 'PENDING', 'Đang chờ giao dịch'
        COMPLETED = 'COMPLETED', 'Đã giao dịch'
        EXPIRED = 'EXPIRED', 'Hết hạn'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='listings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings') # Người đăng tin
    listing_type = models.ForeignKey(ListingType, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    content = RichTextField()
    price = models.DecimalField(max_digits=19, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    view_count = models.PositiveIntegerField(default=0)
    star_average = models.FloatField(default=0.0)

    def __str__(self):
        return self.title

class PropertyMedia(BaseModel):
    """Lưu trữ ảnh/video cho bất động sản"""
    class MediaType(models.TextChoices):
        IMAGE = 'IMAGE', 'Image'
        VIDEO = 'VIDEO', 'Video'
        VIRTUAL_TOUR = 'VIRTUAL_TOUR', 'Virtual Tour'

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='media')
    type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.IMAGE)
    url = CloudinaryField() # Dùng CloudinaryField cho URL
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_thumbnail = models.BooleanField(default=False)

class AnalysisData(BaseModel):
    """Dữ liệu phân tích cho bất động sản"""
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='analysis')
    overview = models.TextField(blank=True, null=True)
    estimated_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)

# =================== INTERACTION ==========================

class Review(BaseModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    point = models.PositiveIntegerField(null=False)
    comment = models.CharField(max_length=255)

    class Meta:
        unique_together = ('user', 'property')

class Wishlist(BaseModel):
    """Danh sách yêu thích của người dùng"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        unique_together = ('user', 'property')

class Appointment(BaseModel):
    """Lịch hẹn xem nhà cho một TIN ĐĂNG cụ thể."""
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Đã lên lịch'
        COMPLETED = 'COMPLETED', 'Đã hoàn thành'
        CANCELLED = 'CANCELLED', 'Đã hủy'
        NO_SHOW = 'NO_SHOW', 'Khách không đến'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='appointments') # SỬA: Trỏ đến Listing
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments_as_agent')
    appointment_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

class ContractType(BaseModel):
    """Loại hợp đồng: Mua bán, Cho thuê, Đặt cọc..."""
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Contract(BaseModel):
    """Hợp đồng giao dịch cho một TIN ĐĂNG cụ thể."""
    class Status(models.TextChoices):
        DRAFTING = 'DRAFTING', 'Đang soạn thảo'
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Chờ thanh toán'
        ACTIVE = 'ACTIVE', 'Đang hiệu lực'
        COMPLETED = 'COMPLETED', 'Đã hoàn tất'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True) # SỬA: Trỏ đến Listing
    contract_type = models.ForeignKey(ContractType, on_delete=models.SET_NULL, null=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts_as_seller')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts_as_buyer')
    money = models.DecimalField(max_digits=19, decimal_places=2)
    content = RichTextField()
    payment_url = models.URLField(max_length=500, blank=True, null=True)
    payment_image = CloudinaryField(blank=True, null=True)
    payment_code = models.CharField(max_length=100, blank=True, null=True)
    signed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFTING)

# =================== SOCIAL ==========================

class Post(BaseModel):
    """Bài đăng trên mạng xã hội của hệ thống"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = RichTextField()

class Comment(BaseModel):
    """Bình luận cho bài đăng"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()

class Reaction(BaseModel):
    """Tương tác (like, love...) cho bài đăng"""
    class Type(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        LOVE = 'LOVE', 'Love'
        HAHA = 'HAHA', 'Haha'
        SAD = 'SAD', 'Sad'
        ANGRY = 'ANGRY', 'Angry'

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')
    type = models.CharField(max_length=10, choices=Type.choices)

    class Meta:
        unique_together = ('user', 'post')

class Subscription(BaseModel):
    """Theo dõi người dùng khác"""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_set')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_set')

    class Meta:
        unique_together = ('follower', 'following')

# =================== NOTIFICATION & REPORT ==========================
class NotificationCategory(BaseModel):
    """Loại thông báo"""
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Notification(BaseModel):
    """Thông báo gửi đến người dùng"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    category = models.ForeignKey(NotificationCategory, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)

class Report(BaseModel):
    """Báo cáo vi phạm"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ xử lý'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang xem xét'
        RESOLVED = 'RESOLVED', 'Đã giải quyết'
        REJECTED = 'REJECTED', 'Từ chối'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_reports')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reports')
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_reports')
    reason = models.TextField()
    resolution_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

class Protest(BaseModel):
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', 'Đang xem xét'
        RESOLVED = 'RESOLVED', 'Đã giải quyết'
        REJECTED = 'REJECTED', 'Từ chối'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True)
    protester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='protests')
    reason = models.TextField()
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_protests')
    resolution_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
