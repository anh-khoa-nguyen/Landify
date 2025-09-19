from django.db import models
from vi_address.models import Ward
from bulk_update_or_create.query import BulkUpdateOrCreateQuerySet

class BaseModel(models.Model):
    """
    Một lớp model trừu tượng cung cấp các trường theo dõi chung.
    - active: Trạng thái hoạt động.
    - created_date: Thời gian tạo.
    - updated_date: Thời gian cập nhật lần cuối.
    """

    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-id"]

class SiteStatistic(models.Model):
    """
    Model để lưu trữ các số liệu thống kê của toàn trang web,
    được tính toán định kỳ bởi các tác vụ nền.
    """
    key = models.CharField(max_length=100, unique=True, primary_key=True
                           , help_text="Khóa định danh cho số liệu, ví dụ: 'total_active_listings'")
    value = models.PositiveIntegerField(default=0, help_text="Giá trị của số liệu")
    last_updated = models.DateTimeField(auto_now=True, help_text="Lần cuối cập nhật")

    def __str__(self):
        return f"{self.key}: {self.value}"

    class Meta:
        verbose_name = "Thống kê Trang"
        verbose_name_plural = "Các Thống kê Trang"


class GeoGridStatistic(models.Model):
    """
    Model để lưu trữ thống kê giá BĐS đã được tính toán trước cho mỗi ô lưới địa lý.
    Dữ liệu được lưu trong JSONField để có thể chứa thống kê cho nhiều ListingCategory.
    """
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    grid_cell_id = models.CharField(
        max_length=100,
        primary_key=True,
        verbose_name="Grid Cell ID"
    )

    # Tọa độ trung tâm của ô lưới (để tham khảo)
    center_lat = models.FloatField(null=True)
    center_lng = models.FloatField(null=True)

    # === TRƯỜNG DỮ LIỆU CHÍNH ĐÃ ĐƯỢC NÂNG CẤP ===
    # stats_by_category sẽ có cấu trúc dạng:
    # {
    #   "27": {  // listing_category_id
    #     "avg_price": 25000000.00,
    #     "count": 15,
    #     "listing_type_code": "RENT",
    #     "property_type_code": "TOWNHOUSE"
    #   },
    #   "15": {
    #     "avg_price_per_m2": 65000000.00,
    #     "count": 8,
    #     "listing_type_code": "BUY_SELL",
    #     "property_type_code": "APARTMENT"
    #   }
    # }
    stats_by_category = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Thống kê theo từng Danh mục"
    )

    # Chúng ta vẫn có thể giữ lại các trường tổng hợp nếu muốn hiển thị nhanh
    # hoặc có thể loại bỏ chúng để đơn giản hóa. Ở đây, tôi sẽ loại bỏ chúng.

    last_updated = models.DateTimeField(auto_now=True, verbose_name="Lần cuối cập nhật")

    def __str__(self):
        return f"Thống kê giá cho ô lưới {self.grid_cell_id}"

    class Meta:
        verbose_name = "Thống kê giá theo Lưới"
        verbose_name_plural = "Các Thống kê giá theo Lưới"