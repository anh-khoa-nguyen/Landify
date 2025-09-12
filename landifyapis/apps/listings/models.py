import builtins
from django.contrib.humanize.templatetags.humanize import intcomma
from datetime import timedelta, timezone

from ckeditor.fields import RichTextField
from django.db import models

from apps.common.models import BaseModel
from apps.properties.models import Property, PropertyType, PropertyFeature, Direction

# Import các model liên quan
from apps.users.models import User

class UnitPrice(models.Model):
    """Model để định nghĩa các loại đơn vị giá."""

    name = models.CharField(max_length=50, unique=True, verbose_name="Tên đơn vị")  # Ví dụ: "triệu/m²", "tỷ"
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã đơn vị")  # Ví dụ: "VND_PER_M2", "VND_BILLION"
    is_per_area_unit = models.BooleanField(default=False, verbose_name="Là đơn vị theo diện tích")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Đơn vị giá"
        verbose_name_plural = "Các Đơn vị giá"

class ListingType(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True,
        help_text="Mã định danh không đổi, ví dụ: BUY_SELL, RENT, PROJECT")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Loại tin đăng"
        verbose_name_plural = "Các Loại tin đăng"

class VipType(BaseModel):
    """
    Model để định nghĩa các loại gói VIP cho tin đăng.
    Chứa các quy tắc nghiệp vụ và dữ liệu có thể tính toán.

    Lưu ý: is_active đã được kế thừa từ BaseModel.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Tên gói VIP")
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã code (cho Frontend)")
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Giá mỗi ngày (VND)")
    sort_priority = models.IntegerField(default=0, verbose_name="Độ ưu tiên sắp xếp")
    boost_multiplier = models.IntegerField(default=1, verbose_name="Hệ số nhân (ví dụ: 30 cho X30)")
    allow_auto_top_up = models.BooleanField(default=False, verbose_name="Cho phép tự động đẩy tin")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Loại tin VIP"
        verbose_name_plural = "Các loại tin VIP"
        ordering = ["-sort_priority"]

class ListingPropertyFeatureValue(BaseModel):
    """
    Bảng trung gian lưu giá trị cụ thể của một đặc điểm cho một tin đăng.
    Ví dụ: Tin đăng A có đặc điểm "Mặt tiền" với giá trị là "5.5" (m).
    """

    listing = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="feature_values")
    feature = models.ForeignKey(PropertyFeature, on_delete=models.CASCADE, related_name="listing_values")

    value = models.JSONField(verbose_name="Giá trị")

    def __str__(self):
        return f"{self.listing.title} - {self.feature.name}: {str(self.value)}"

    @property
    def display_value(self):
        """
        Một property để hiển thị giá trị một cách thân thiện trên trang admin hoặc API.
        """
        feature_type = self.feature.feature_type
        if feature_type == PropertyFeature.FeatureType.DIRECTION:
            try:
                direction_id = int(self.value)
                direction = Direction.objects.get(pk=direction_id)
                return direction.name
            except (ValueError, TypeError, Direction.DoesNotExist):
                return "Không rõ"
        return self.value

    class Meta:
        verbose_name = "Giá trị Đặc điểm của Tin đăng"
        verbose_name_plural = "Các Giá trị Đặc điểm của Tin đăng"
        unique_together = ("listing", "feature")


class Listing(BaseModel):
    """Model Tin đăng - Chứa thông tin của một lần chào bán/cho thuê."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Đang đăng"
        PENDING = "PENDING", "Đang chờ giao dịch"
        COMPLETED = "COMPLETED", "Đã giao dịch"
        CANCELLED = "CANCELLED", "Đã hủy"

    class SpamCheckStatus(models.TextChoices):
        PENDING = "PENDING", "Chờ kiểm tra"
        CLEAN = "CLEAN", "Trong sạch"
        FLAGGED = "FLAGGED", "Bị đánh dấu spam"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="listings", verbose_name="Bất động sản"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings", verbose_name="Người đăng tin")
    listing_type = models.ForeignKey(
        ListingType, on_delete=models.SET_NULL, null=True, verbose_name="Loại tin đăng (Bán/Thuê/Dự án)"
    )
    title = models.CharField(max_length=255, verbose_name="Tiêu đề")
    content = RichTextField(verbose_name="Nội dung")
    price_value = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True, verbose_name="Giá trị (số)"
    )
    unit_price = models.ForeignKey(
        UnitPrice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Đơn vị giá"
    )
    features = models.ManyToManyField(
        PropertyFeature,
        through=ListingPropertyFeatureValue,
        related_name="listings",
        verbose_name="Các đặc điểm chi tiết",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE, verbose_name="Trạng thái"
    )
    spam_check_status = models.CharField(
        max_length=20, choices=SpamCheckStatus.choices, default=SpamCheckStatus.PENDING, verbose_name="Trạng thái Spam"
    )
    commission_percentage = models.FloatField(verbose_name="Phần trăm hoa hồng (%)", default=0.0)

    @builtins.property
    def display_price(self):
        if self.price_value is None:
            return "Giá thỏa thuận"

        formatted_value = intcomma(int(self.price_value))

        if self.unit_price is None:
            return f"{formatted_value} VND"  # Mặc định là VND nếu không có đơn vị

            # Nếu đơn vị là VND, chỉ cần thêm "VND"
        if self.unit_price.code == 'VND':
            return f"{formatted_value} VND"

            # Nếu là các đơn vị khác, nối số và đơn vị lại
            # Ví dụ: "6,452,147 /m²" hoặc "85,000,000 /tháng"
        return f"{formatted_value} {self.unit_price.name}"

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Tin đăng"
        verbose_name_plural = "Các Tin đăng"


class ListingVip(BaseModel): # Vẫn kế thừa BaseModel để có created_date, updated_date
    """
    Lưu trữ trạng thái VIP hiện tại của một Tin đăng.
    """
    listing = models.OneToOneField( # <-- THAY ĐỔI: OneToOneField
        Listing,
        on_delete=models.CASCADE,
        related_name="vip_status",
        verbose_name="Tin đăng",
        primary_key=True
    )
    vip_type = models.ForeignKey(
        VipType,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Loại gói VIP hiện tại"
    )

    end_date = models.DateTimeField(
        verbose_name="Ngày kết thúc VIP",
        null=True,
        blank=True
    )

    @property
    def is_active(self):
        """Kiểm tra xem trạng thái VIP có còn hoạt động không."""
        if not self.end_date or not self.vip_type:
            return False
        return timezone.now() <= self.end_date

    def __str__(self):
        if self.is_active:
            return f"{self.listing.title} - {self.vip_type.name} (còn hiệu lực)"
        return f"{self.listing.title} - Không có VIP"

    class Meta:
        verbose_name = "Trạng thái VIP của Tin đăng"
        verbose_name_plural = "Các trạng thái VIP của Tin đăng"

#====================DETAILS=======================

class BuySellDetail(BaseModel):
    """Lưu các trường chỉ dành riêng cho tin đăng Mua/Bán."""

    class ConditionStatus(models.TextChoices):
        NEW = "NEW", "Mới 100%"
        RENOVATED = "RENOVATED", "Đã cải tạo"
        GOOD = "GOOD", "Tình trạng tốt"
        NEEDS_REPAIR = "NEEDS_REPAIR", "Cần sửa chữa"

    listing = models.OneToOneField(
        "Listing", on_delete=models.CASCADE, related_name="buysell_detail", verbose_name="Tin đăng"
    )
    is_mortgaged = models.BooleanField(null=True, blank=True, verbose_name="Đang thế chấp ngân hàng?")
    condition_status = models.CharField(
        max_length=20, choices=ConditionStatus.choices, null=True, blank=True, verbose_name="Tình trạng hiện tại"
    )

    class Meta:
        verbose_name = "Chi tiết tin Bán/Mua"
        verbose_name_plural = "Các chi tiết tin Bán/Mua"

    def __str__(self):
        return f"Chi tiết mua bán: {self.listing.title}"

class RentalDetail(BaseModel):
    """Lưu các trường chỉ dành riêng cho tin đăng Cho Thuê."""

    listing = models.OneToOneField(
        "Listing", on_delete=models.CASCADE, related_name="rental_detail", verbose_name="Tin đăng"
    )
    deposit_amount = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True, verbose_name="Số tiền cọc"
    )
    min_lease_duration = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Thời hạn thuê tối thiểu (tháng)"
    )
    allow_pets = models.BooleanField(
        null=True, blank=True, verbose_name="Cho phép nuôi thú cưng"
    )  # null = true <=> Có/Không/Không đề cập
    allow_smoking = models.BooleanField(null=True, blank=True, verbose_name="Cho phép hút thuốc")
    max_occupants = models.PositiveIntegerField(null=True, blank=True, verbose_name="Số người ở tối đa")
    is_electricity_included = models.BooleanField(default=False, verbose_name="Giá thuê đã bao gồm điện")
    is_water_included = models.BooleanField(default=False, verbose_name="Giá thuê đã bao gồm nước")
    is_internet_included = models.BooleanField(
        default=False, verbose_name="Giá thuê đã bao gồm Internet/Truyền hình cáp"
    )
    is_management_fee_included = models.BooleanField(default=False, verbose_name="Giá thuê đã bao gồm phí quản lý")
    available_from_date = models.DateField(null=True, blank=True, verbose_name="Ngày có thể dọn vào")

    class Meta:
        verbose_name = "Chi tiết tin Cho thuê"
        verbose_name_plural = "Các chi tiết tin Cho thuê"

    def __str__(self):
        return f"Chi tiết cho thuê: {self.listing.title}"

class ProjectDetail(BaseModel):
    """Lưu các trường chỉ dành riêng cho tin đăng Dự án."""

    listing = models.OneToOneField(
        "Listing", on_delete=models.CASCADE, related_name="project_detail", verbose_name="Tin đăng"
    )
    developer = models.CharField(max_length=255, verbose_name="Chủ đầu tư")
    total_area = models.CharField(max_length=50, null=True, blank=True, verbose_name="Tổng diện tích đất dự án")
    building_density = models.FloatField(null=True, blank=True, verbose_name="Mật độ xây dựng (%)")
    scale_description = models.TextField(null=True, blank=True, verbose_name="Mô tả quy mô")

    total_units = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tổng số căn")
    product_types = models.ManyToManyField(PropertyType, blank=True, verbose_name="Các loại hình sản phẩm trong dự án")
    unit_area_range = models.CharField(max_length=100, null=True, blank=True, verbose_name="Khoảng diện tích sản phẩm")

    ownership_form = models.CharField(max_length=255, null=True, blank=True, verbose_name="Hình thức sở hữu")
    launch_date = models.DateField(null=True, blank=True, verbose_name="Ngày mở bán")
    handover_date = models.DateField(null=True, blank=True, verbose_name="Ngày bàn giao (dự kiến)")

    class Meta:
        verbose_name = "Chi tiết tin Dự án"
        verbose_name_plural = "Các chi tiết tin Dự án"

    def __str__(self):
        return f"Chi tiết dự án cho: {self.listing.title}"


class PromotionRule(BaseModel):
    """
    Định nghĩa các QUY TẮC và khuôn mẫu cho một chương trình khuyến mãi.
    """

    class PromotionType(models.TextChoices):
        FREE_LISTING = "FREE_LISTING", "Miễn phí Tin đăng"
        DISCOUNT_VIP = "DISCOUNT_VIP", "Giảm giá Gói VIP"

    class TriggerEvent(models.TextChoices):
        ON_SIGNUP = "ON_SIGNUP", "Khi đăng ký tài khoản"
        MANUAL = "MANUAL", "Gán thủ công bởi admin"

    # --- Thông tin cơ bản ---
    title = models.CharField(max_length=255, verbose_name="Tên chương trình KM")
    description = models.TextField(verbose_name="Mô tả chi tiết")
    promo_type = models.CharField(max_length=20, choices=PromotionType.choices, verbose_name="Loại khuyến mãi")

    # --- Thông tin về giá trị KM ---
    free_listing_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Số ngày đăng tin miễn phí")
    discount_percentage = models.FloatField(null=True, blank=True, verbose_name="Phần trăm giảm giá VIP")
    applicable_vip_types = models.ManyToManyField(VipType, blank=True, verbose_name="Áp dụng cho các gói VIP")

    # === LOGIC MỚI CHO THỜI HẠN ĐỘNG ===
    trigger_event = models.CharField(
        max_length=20,
        choices=TriggerEvent.choices,
        default=TriggerEvent.MANUAL,
        verbose_name="Sự kiện kích hoạt"
    )
    # Số ngày hiệu lực KỂ TỪ KHI được kích hoạt
    validity_duration = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Thời hạn hiệu lực (số ngày)",
        help_text="Để trống nếu KM được gán thủ công với ngày hết hạn cụ thể."
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Quy tắc Khuyến mãi"
        verbose_name_plural = "Các Quy tắc Khuyến mãi"


# Model mới để lưu trữ khuyến mãi đã được áp dụng cho người dùng
class UserPromotion(BaseModel):
    """
    Một bản ghi cụ thể của một khuyến mãi đã được cấp cho người dùng.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Có thể sử dụng"
        USED = "USED", "Đã sử dụng"
        EXPIRED = "EXPIRED", "Đã hết hạn"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_promotions")
    # Liên kết đến quy tắc gốc để lấy thông tin (title, description, giá trị KM)
    rule = models.ForeignKey(PromotionRule, on_delete=models.CASCADE, related_name="instances")
    # Mã code duy nhất cho lần sử dụng này, có thể giống với code của rule hoặc là duy nhất
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã khuyến mãi")

    # Ngày hết hạn CỤ THỂ được tính toán cho user này
    expiry_date = models.DateTimeField(verbose_name="Ngày hết hạn")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    # Lưu lại thời điểm và đối tượng đã sử dụng mã này
    used_at = models.DateTimeField(null=True, blank=True)
    used_on_listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"KM '{self.rule.title}' cho {self.user.username}"

    class Meta:
        verbose_name = "Khuyến mãi của Người dùng"
        verbose_name_plural = "Các Khuyến mãi của Người dùng"
        ordering = ['-expiry_date']