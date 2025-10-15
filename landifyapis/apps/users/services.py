# landifys/services/accounts.py

from typing import IO

import cloudinary
import cloudinary.uploader
from django.db import transaction

from ..common.services import BusinessLogicError
from .models import Subscription, User, UserProfile
from .serializers import UserCreateSerializer


def create_user(serializer: UserCreateSerializer) -> User:
    """Tạo một người dùng mới và các đối tượng liên quan."""
    with transaction.atomic():
        user = User.objects.create_user(**serializer.validated_data)
        UserProfile.objects.create(user=user)
    return user


def change_user_password(*, user: User, old_password: str, new_password: str):
    """Thay đổi mật khẩu cho người dùng đã đăng nhập."""
    if not user.check_password(old_password):
        raise BusinessLogicError("Mật khẩu cũ không chính xác.")
    user.set_password(new_password)
    user.save(update_fields=["password"])


def change_user_avatar(*, user: User, avatar_file: IO) -> str:
    """Xử lý việc upload ảnh đại diện mới và cập nhật cho người dùng."""
    try:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.avatar = avatar_file
        profile.save(update_fields=["avatar"])

        return profile.avatar.url
    except Exception as e:
        raise BusinessLogicError(f"Upload ảnh thất bại: {e}")

def toggle_user_follow(*, follower: User, following: User) -> str:
    """Xử lý logic theo dõi hoặc bỏ theo dõi một người dùng khác."""
    if follower == following:
        raise BusinessLogicError("Bạn không thể tự theo dõi chính mình.")

    subscription, created = Subscription.objects.get_or_create(follower=follower, following=following)

    if created:
        return "followed"
    else:
        subscription.delete()
        return "unfollowed"
