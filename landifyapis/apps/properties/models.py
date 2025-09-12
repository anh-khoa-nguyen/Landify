# landifys/models/property.py
from cloudinary.models import CloudinaryField
from django.contrib.gis.db import models as gis_models
from django.db import models
from vi_address.models import City, District, Ward

from apps.common.models import BaseModel
from apps.users.models import User
import cloudinary

class PropertyType(BaseModel):
    """Loại bất động sản (VD: Căn hộ, Nhà phố, Đất nền)"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Mã code")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Loại Bất động sản"
        verbose_name_plural = "Các Loại Bất động sản"

class Direction(BaseModel):
    """Hướng nhà (VD: Đông, Tây, Nam, Bắc)"""

    name = models.CharField(max_length=50, unique=True, help_text="Tên hướng, ví dụ: Đông, Tây Nam")
    code = models.CharField(max_length=20, unique=True, null=True, blank=True,
                            help_text="Mã không đổi, ví dụ: EAST, WEST")
    element = models.CharField(max_length=20, help_text="Hành tương ứng, ví dụ: Mộc, Kim, Hỏa")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Hướng"
        verbose_name_plural = "Các Hướng"


class Location(BaseModel):
    """Lưu địa chỉ có cấu trúc của bất động sản"""

    street = models.CharField(max_length=255, verbose_name="Số nhà, Tên đường")
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, verbose_name="Phường/Xã")
    point = gis_models.PointField(srid=4326, null=True, blank=True, verbose_name="Tọa độ")

    @property
    def district(self):
        return self.ward.parent_code if self.ward else None

    @property
    def city(self):
        return self.ward.parent_code.parent_code if self.ward and self.ward.parent_code else None

    def __str__(self):
        return f"{self.street}, {self.ward}, {self.district}, {self.city}"

    class Meta:
        verbose_name = "Địa điểm"
        verbose_name_plural = "Các Địa điểm"


# class Utility(BaseModel):
#     """Tiện ích (VD: Hồ bơi, Phòng gym, Gần trường học)"""
#     class UtilityType(models.TextChoices):
#         INTERIOR = "INTERIOR", "Nội thất"
#         AMENITY = "AMENITY", "Tiện nghi trong nhà/dự án"
#         NEARBY = "NEARBY", "Tiện ích lân cận"
#         OTHER = "OTHER", "Khác"
#
#     name = models.CharField(max_length=100, unique=True)
#     code = models.CharField(max_length=50, unique=True, null=True, blank=True,
#                             help_text="Mã định danh không đổi cho frontend, ví dụ: FULL_INTERIOR")
#     utility_type = models.CharField(
#         max_length=20,
#         choices=UtilityType.choices,
#         default=UtilityType.AMENITY,  # Giữ nguyên default hoặc đổi thành OTHER nếu muốn
#         verbose_name="Loại tiện ích"
#     )
#
#     def __str__(self):
#         return f"{self.name} ({self.get_utility_type_display()})"
#
#     class Meta:
#         verbose_name = "Tiện ích"
#         verbose_name_plural = "Các Tiện ích"


class LegalStatus(BaseModel):
    """
    Model để định nghĩa các loại tình trạng pháp lý.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Tên tình trạng pháp lý")
    code = models.CharField(max_length=50, unique=True, null=True, blank=True,
                            help_text="Mã không đổi, ví dụ: SOHONG, HDMB")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả/Giải thích")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tình trạng pháp lý"
        verbose_name_plural = "Các Tình trạng pháp lý"

class Property(BaseModel):
    """Model Bất động sản - Chỉ chứa các thông tin vật lý, cố định của tài sản."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="properties", verbose_name="Chủ sở hữu")
    property_type = models.ForeignKey(
        PropertyType, on_delete=models.SET_NULL, null=True, verbose_name="Loại hình BĐS (để thống kê)"
    )
    location = models.OneToOneField(Location, on_delete=models.SET_NULL, null=True, verbose_name="Địa điểm")
    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hướng")
    area = models.FloatField(verbose_name="Diện tích (m²)")
    legal_status = models.ForeignKey(
        LegalStatus, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tình trạng pháp lý"
    )
    # bedroom_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Số phòng ngủ")
    # bathroom_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Số phòng tắm")

    class Meta:
        verbose_name = "Bất động sản"
        verbose_name_plural = "Các Bất động sản"

    def __str__(self):
        return f"BĐS của {self.owner} tại {self.location}"

class PropertyFeature(BaseModel):
    """
    Model để định nghĩa các đặc điểm, thuộc tính có thể có của một BĐS.
    Ví dụ: "Mặt tiền", "Hướng ban công", "Tình trạng nội thất".
    """

    class Category(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Đặc điểm kỹ thuật"  # Hướng, số phòng, diện tích...
        INTERIOR = "INTERIOR", "Nội thất"
        AMENITY = "AMENITY", "Tiện nghi trong nhà/dự án"
        NEARBY = "NEARBY", "Tiện ích lân cận"
        OTHER = "OTHER", "Khác"

    class FeatureType(models.TextChoices):
        BOOLEAN = "BOOLEAN", "Có / Không"  # Ví dụ: Có chỗ đỗ ô tô
        FLOAT = "FLOAT", "Số thực"  # Ví dụ: Mặt tiền (m)
        TEXT = "TEXT", "Văn bản"  # Ví dụ: Tình trạng nội thất
        DIRECTION = "DIRECTION", "Hướng"  # Ví dụ: Hướng ban công

    name = models.CharField(max_length=100, unique=True, verbose_name="Tên đặc điểm")
    code = models.CharField(
        max_length=50,
        unique=True,
        null=True,  # Tạm thời cho phép null để không ảnh hưởng các bản ghi cũ
        blank=True,
        help_text="Mã không đổi cho API, ví dụ: NUM_BEDROOMS"
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TECHNICAL,
        verbose_name="Phân loại (Category)"
    )

    feature_type = models.CharField(
        max_length=10,
        choices=FeatureType.choices,
        default=FeatureType.BOOLEAN,
        verbose_name="Loại giá trị"
    )

    applicable_property_types = models.ManyToManyField(
        "PropertyType", blank=True, verbose_name="Áp dụng cho các loại BĐS"
    )

    def __str__(self):
        return f"{self.name} ({self.get_feature_type_display()})"

    class Meta:
        verbose_name = "Đặc điểm Bất động sản"
        verbose_name_plural = "Các Đặc điểm Bất động sản"

class PropertyMedia(BaseModel):
    """Lưu trữ ảnh/video cho bất động sản"""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="media", verbose_name="Bất động sản")
    url = CloudinaryField("media", resource_type="auto")
    public_id = models.CharField(max_length=255, editable=False, help_text="Public ID từ Cloudinary để xóa file")

    def __str__(self):
        return f"Media for Property {self.property.id}"

    class Meta:
        verbose_name = "Media Bất động sản"
        verbose_name_plural = "Các Media Bất động sản"


