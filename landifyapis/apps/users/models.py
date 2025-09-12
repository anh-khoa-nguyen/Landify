# landifys/models/user.py
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import BaseModel

class User(AbstractUser):
    """
    Model người dùng tùy chỉnh, kế thừa từ AbstractUser của Django.
    """
    class Role(models.TextChoices):
        ADMIN = "admin", "Quản trị viên"
        USER = "user", "Người dùng"

    class Gender(models.TextChoices):
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        OTHER = "other", "Khác"

    # Thông tin cơ bản
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, verbose_name="Vai trò")
    phone_number = models.CharField(
        max_length=15, unique=True, null=True, blank=True, db_index=True, verbose_name="Số điện thoại"
    )
    # Cờ xác thực
    is_phone_verified = models.BooleanField(default=False, verbose_name="Đã xác thực SĐT")
    is_id_card_verified = models.BooleanField(default=False, verbose_name="Đã quét CCCD")
    is_identity_verified = models.BooleanField(default=False, verbose_name="Đã xác thực danh tính (eKYC)")

    firebase_uid = models.CharField(
        max_length=128, unique=True, null=True, blank=True, db_index=True, verbose_name="Firebase UID"
    )
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.get_full_name() or self.username


class UserProfile(BaseModel):
    """
    Model lưu trữ thông tin hồ sơ mở rộng cho người dùng.
    """

    # --- Liên kết và Thông tin cá nhân ---
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Người dùng")
    avatar = CloudinaryField(null=True, blank=True, verbose_name="Ảnh đại diện")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    gender = models.CharField(
        max_length=10, choices=User.Gender.choices, null=True, blank=True, verbose_name="Giới tính"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Giới thiệu bản thân")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vị trí (Tỉnh/Thành phố)")

    # --- Dữ liệu từ eKYC (sẽ được điền sau khi xác thực) ---
    nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name="Quốc tịch")
    home_town = models.CharField(max_length=255, blank=True, null=True, verbose_name="Quê quán")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Địa chỉ thường trú")
    id_card_number = models.CharField(
        max_length=15, unique=True, null=True, blank=True, db_index=True, verbose_name="Số CCCD/CMND"
    )

    # --- Dữ liệu thống kê (suy diễn, được cập nhật tự động) ---
    rating_score = models.FloatField(default=0.0, verbose_name="Điểm đánh giá trung bình")
    rating_count = models.PositiveIntegerField(default=0, verbose_name="Tổng số lượt đánh giá")
    listing_count = models.PositiveIntegerField(default=0, verbose_name="Tổng số tin đăng hoạt động")

    # --- Thông tin chứng chỉ (nếu có) ---
    has_certificate = models.BooleanField(default=False, verbose_name="Có chứng chỉ môi giới")

    def __str__(self):
        return f"Hồ sơ của {self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "Hồ sơ Người dùng"
        verbose_name_plural = "Các Hồ sơ Người dùng"


class Subscription(BaseModel):
    """Theo dõi người dùng khác"""

    follower = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="following_set", verbose_name="Người theo dõi"
    )
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="follower_set", verbose_name="Người được theo dõi"
    )

    class Meta:
        unique_together = ("follower", "following")
        verbose_name = "Lượt theo dõi"
        verbose_name_plural = "Các Lượt theo dõi"
