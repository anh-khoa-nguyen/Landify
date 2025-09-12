from django.db import models

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
