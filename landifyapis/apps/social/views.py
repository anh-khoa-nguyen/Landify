from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

import apps.common.perms as perms
from apps.common.docs import social_docs

from . import models
from . import services as social_services
from .serializers import CommentSerializer, PostSerializer, ReactionSerializer

# ==============================================================================
# SOCIAL VIEWS
# ==============================================================================


@social_docs.post_viewset_schema
class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho các bài đăng trên mạng xã hội.
    Hỗ trợ CRUD cơ bản và hành động 'react'.
    """

    queryset = models.Post.objects.annotate(comment_count=Count("comments"), reaction_count=Count("reactions")).filter(
        active=True
    )

    serializer_class = PostSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action in ["create", "react"]:
            return [permissions.IsAuthenticated()]
        # Chỉ chủ sở hữu hoặc admin mới được sửa/xóa
        return [perms.IsOwnerOrAdmin()]

    def get_serializer_context(self):
        """
        Truyền request vào context để serializer có thể lấy current_user.
        Cần thiết cho trường 'current_user_reaction'.
        """
        return {"request": self.request}

    def perform_create(self, serializer):
        """Tự động gán người đăng bài là người dùng hiện tại."""
        serializer.save(user=self.request.user)

    @social_docs.react_post_schema
    @action(methods=["post"], detail=True)
    def react(self, request, pk=None):
        """
        Thêm, sửa, hoặc xóa một cảm xúc cho bài đăng.
        """
        post = self.get_object()
        serializer = ReactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reaction_type = serializer.validated_data["type"]

        status_code, reaction_obj = social_services.process_post_reaction(
            user=request.user, post=post, reaction_type=reaction_type
        )

        if status_code == "created":
            return Response(ReactionSerializer(reaction_obj).data, status=status.HTTP_201_CREATED)
        elif status_code == "updated":
            return Response(ReactionSerializer(reaction_obj).data, status=status.HTTP_200_OK)
        else:  # 'deleted'
            return Response(status=status.HTTP_204_NO_CONTENT)


@social_docs.comment_viewset_schema
class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho bình luận, lồng trong một Post.
    URL: /api/posts/{post_pk}/comments/
    """

    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Chỉ trả về các bình luận của bài đăng được chỉ định trong URL."""
        return models.Comment.objects.filter(post_id=self.kwargs.get("post_pk"), active=True).select_related(
            "user__profile"
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [perms.IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        """Tự động gán người bình luận và bài đăng."""
        post = get_object_or_404(models.Post, pk=self.kwargs.get("post_pk"))
        serializer.save(user=self.request.user, post=post)
