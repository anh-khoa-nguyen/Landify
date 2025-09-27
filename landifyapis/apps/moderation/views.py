from rest_framework import generics, parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.common import perms
from apps.common.docs import moderation_docs

from .models import Protest, Report, User, ModerationAction
from .serializers import ProtestSerializer, ReportSerializer
from . import services as moderation_services
from ..common.services import BusinessLogicError

from apps.users.serializers import UserSerializer
from apps.users import services as accounts_services

# =================== REPORT & PROTEST (ADMINISTRATION) ==========================

@moderation_docs.report_viewset_schema
class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet để người dùng tạo báo cáo và admin quản lý."""

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return self.queryset
        return self.queryset.filter(reporter=user)

    def perform_create(self, serializer):
        serializer.save(
            reporter=self.request.user,
            reported_item_type=serializer.validated_data['reported_item_type']
        )

@moderation_docs.protest_viewset_schema
class ProtestViewSet(viewsets.ModelViewSet):
    """ViewSet chỉ dành cho Admin để quản lý và xử lý các kháng nghị."""

    queryset = Protest.objects.select_related("protester", "listing", "admin").all()
    serializer_class = ProtestSerializer

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [perms.IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return self.queryset
        return self.queryset.filter(protester=user)

    def perform_create(self, serializer):
        action_id = serializer.validated_data.get('action_id')
        try:
            action = ModerationAction.objects.get(pk=action_id)
            moderation_services.create_protest(
                action=action,
                protester=self.request.user,
                reason=serializer.validated_data.get('reason')
            )
        except ModerationAction.DoesNotExist:
            raise BusinessLogicError("Hành động xử lý không tồn tại.")
        except BusinessLogicError as e:
            raise e