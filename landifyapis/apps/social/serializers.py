from rest_framework import serializers

from apps.common.mixins import DynamicFieldsMixin
from apps.users.models import Subscription
from apps.users.serializers import UserSerializer

from .models import Comment, Post, Reaction


class PostSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer chính cho model Post, bao gồm các thông tin tổng hợp."""

    user = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))

    comment_count = serializers.IntegerField(read_only=True)
    reaction_count = serializers.IntegerField(read_only=True)

    current_user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "title",
            "content",
            "created_date",
            "updated_date",
            "comment_count",
            "reaction_count",
            "current_user_reaction",
        ]
        read_only_fields = ["user"]

    def get_current_user_reaction(self, obj) -> str | None:
        """
        Lấy loại cảm xúc của người dùng đang đăng nhập trên bài đăng này.
        """
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            # Tìm reaction của user này trên post `obj`
            reaction = obj.reactions.filter(user=request.user).first()
            return reaction.type if reaction else None
        return None


class CommentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Comment."""

    user = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))

    class Meta:
        model = Comment
        fields = "__all__"
        read_only_fields = ["user", "post"]


class ReactionSerializer(serializers.ModelSerializer):
    """Serializer đơn giản để validate loại cảm xúc."""

    class Meta:
        model = Reaction
        fields = ["type"]
