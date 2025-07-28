from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.utils import timezone

#=================== USER & BASE ==========================

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        UNKNOWING = 'unknowing', 'Unknowing'

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWING)
    phone_number = models.CharField(max_length=15, null=True, blank=True, unique=True)
    avatar = CloudinaryField(null=True, blank=True)

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)  # Mỗi lần cập nhật tự lấy ngày hiện tại

    class Meta:
        abstract = True

#=================== BẤT ĐỘNG SẢN ==========================

class Category(BaseModel):
    name = models.CharField(max_length=50)

class Property(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ duyệt'
        REVIEWING = 'reviewing', 'Đang duyệt'
        APPROVED = 'approved', 'Đã duyệt'
        REJECTED = 'rejected', 'Bị từ chối'
        COMPLETED = 'completed', 'Kết thúc'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    content = RichTextField(null=False, default='a')
    note = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    acreage = models.FloatField(default=0)
    address = models.CharField(max_length=255)
    lat = models.FloatField(default=0)
    lng = models.FloatField(default=0)
    has_legal_docs = models.BooleanField(default=False);
    floor_num = models.IntegerField()
    naproom_num = models.PositiveIntegerField()
    restroom_num = models.PositiveIntegerField()
    status = models.CharField(max_length=50, choices=Status,
                              default='pending')
    star_average = models.FloatField(default=0)

class AnalysisData(BaseModel):
    property = models.OneToOneField(Property, null=True, on_delete=models.CASCADE)
    overview = models.CharField(max_length=50)

class Review(BaseModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    point = models.PositiveIntegerField(null=False)
    comment = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'property')

#=================== MẠNG XÃ HỘI ==========================

class Post(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = RichTextField(null=False, default='a')

class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = RichTextField(null=False, default='a')



#=================== THÔNG BÁO ==========================
class NotificationCate(BaseModel):
    name = models.CharField(max_length=50, unique=True)

class Notification(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(NotificationCate, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=50)
    content = models.CharField(max_length=550)
    is_read = models.BooleanField(default=False)
