from ckeditor.fields import RichTextField
from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User

class Post(BaseModel):
    """Bài đăng trên mạng xã hội của hệ thống"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts", verbose_name="Người đăng")
    title = models.CharField(max_length=255, verbose_name="Tiêu đề")
    content = RichTextField(verbose_name="Nội dung")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Bài đăng"
        verbose_name_plural = "Các Bài đăng"


class Comment(BaseModel):
    """Bình luận cho bài đăng"""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments", verbose_name="Bài đăng")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments", verbose_name="Người bình luận")
    content = models.TextField(verbose_name="Nội dung")

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Các Bình luận"


class Reaction(BaseModel):
    """Tương tác (like, love...) cho bài đăng"""

    class Type(models.TextChoices):
        LIKE = "like", "Thích"
        LOVE = "love", "Yêu thích"
        HAHA = "haha", "Haha"
        WOW = "wow", "Wow"
        SAD = "sad", "Buồn"
        ANGRY = "angry", "Giận dữ"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions", verbose_name="Bài đăng")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reactions", verbose_name="Người tương tác")
    type = models.CharField(max_length=10, choices=Type.choices, verbose_name="Loại cảm xúc")

    class Meta:
        unique_together = ("user", "post")
        verbose_name = "Cảm xúc"
        verbose_name_plural = "Các Cảm xúc"


