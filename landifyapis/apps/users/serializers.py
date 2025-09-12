# landifys/serializers/accounts.py

from rest_framework import serializers

from apps.common.mixins import DynamicFieldsMixin
from apps.users.models import User, UserProfile

class UserProfileSimpleSerializer(serializers.ModelSerializer):
    """Serializer đơn giản chỉ để lấy avatar và các thông tin cần thiết khác."""
    class Meta:
        model = UserProfile
        fields = ['avatar']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['avatar'] = instance.avatar.url if instance.avatar else None

        return rep


class UserSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer chính để hiển thị thông tin User."""
    profile = UserProfileSimpleSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "get_full_name",
            "email",
            "role",
            "phone_number",
            "is_phone_verified",
            "is_id_card_verified",
            "is_identity_verified",
            "date_joined",
            "profile",
        ]
        # Thêm UserProfile nếu cần
        # profhile = UserProfileSerializer(read_only=True)

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['gender', 'date_of_birth']

class UserUpdateSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer dùng khi người dùng tự cập nhật hồ sơ."""
    profile = UserProfileUpdateSerializer(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile"]

    def update(self, instance, validated_data):
        # Tách dữ liệu của profile ra khỏi validated_data
        profile_data = validated_data.pop('profile', None)

        # Cập nhật các trường của User model như bình thường
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Nếu có dữ liệu profile được gửi lên, cập nhật UserProfile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(
                user=instance,
                defaults=profile_data
            )
            if not created:
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer riêng cho việc tạo người dùng mới."""

    class Meta:
        model = User
        fields = ["username", "password", "phone_number", "first_name", "last_name"]
        extra_kwargs = {
            "password": {"write_only": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# =======================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer con để chỉ lấy dữ liệu từ UserProfile."""
    class Meta:
        model = UserProfile
        fields = [
            'avatar',
            'description',
            'rating_score',
            'rating_count',
            'listing_count',
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['avatar'] = instance.avatar.url if instance.avatar else None
        return rep


class UserProfileDetailSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serializer chuyên dụng để hiển thị trang hồ sơ công khai của một người dùng.
    """
    # Lồng dữ liệu từ UserProfile model vào đây
    profile = UserProfileSerializer(read_only=True)

    # Thêm các trường thống kê về theo dõi
    follower_count = serializers.IntegerField(source='follower_set.count', read_only=True)
    following_count = serializers.IntegerField(source='following_set.count', read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "get_full_name",
            "date_joined",
            "profile",  # Dữ liệu lồng nhau từ UserProfile
            "follower_count",
            "following_count",
        ]