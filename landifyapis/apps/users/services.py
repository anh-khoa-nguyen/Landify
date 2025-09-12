# landifys/services/accounts.py

from typing import IO

import cloudinary
import cloudinary.uploader
from django.db import transaction

from .models import User, UserProfile,Subscription
from .serializers import UserCreateSerializer

from ..common.services import BusinessLogicError

def create_user(serializer: UserCreateSerializer) -> User:
    """Tạo một người dùng mới và các đối tượng liên quan."""
    with transaction.atomic():
        # Dùng create_user để hash password đúng cách
        user = User.objects.create_user(**serializer.validated_data)
        # Tự động tạo UserProfile ngay khi tạo User
        UserProfile.objects.create(user=user)

    # Kích hoạt các tác vụ nền sau khi đăng ký thành công
    # tasks.users.send_welcome_email.delay(user.id)

    return user


def change_user_password(*, user: User, old_password: str, new_password: str):
    """Thay đổi mật khẩu cho người dùng đã đăng nhập."""
    if not user.check_password(old_password):
        raise BusinessLogicError("Mật khẩu cũ không chính xác.")

    # Django sẽ tự động hash password mới
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


def disable_user_account(*, admin_user: User, user_to_disable: User) -> bool:
    """[ADMIN] Vô hiệu hóa hoặc kích hoạt lại tài khoản người dùng."""
    if user_to_disable.is_superuser or user_to_disable == admin_user:
        raise BusinessLogicError("Không thể vô hiệu hóa tài khoản này.")

    user_to_disable.is_active = not user_to_disable.is_active
    user_to_disable.save(update_fields=["is_active"])
    return user_to_disable.is_active


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
