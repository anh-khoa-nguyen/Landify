from rest_framework import generics, parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.common import perms
from apps.common.docs import moderation_docs

from .models import Protest, Report, User, ModerationAction
from .serializers import ProtestSerializer, ReportSerializer, ModerationActionSerializer
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
        return self.queryset.filter(reporter=user)  # Người dùng chỉ xem báo cáo của mình

    def perform_create(self, serializer):
        # Serializer đã validate và thêm content_type vào data
        serializer.save(
            reporter=self.request.user,
            reported_item_type=serializer.validated_data['reported_item_type']
        )

    @action(detail=True, methods=['post'], url_path='take-action', permission_classes=[perms.IsAdmin])
    def take_action(self, request, pk=None):
        report = self.get_object()
        action_type = request.data.get('action_type')
        reason = request.data.get('reason')
        # Gọi service để xử lý
        action_obj = moderation_services.take_moderation_action(
            moderator=request.user, report=report, action_type=action_type, reason=reason
        )
        return Response(ModerationActionSerializer(action_obj).data, status=status.HTTP_201_CREATED)

@moderation_docs.protest_viewset_schema
class ProtestViewSet(viewsets.ModelViewSet):
    """ViewSet chỉ dành cho Admin để quản lý và xử lý các kháng nghị."""

    queryset = Protest.objects.select_related("protester", "listing", "admin").all()
    serializer_class = ProtestSerializer

    def get_permissions(self):
        # Người dùng thường có thể tạo và xem kháng nghị của mình
        if self.action in ['create', 'list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        # Admin có thể làm mọi thứ
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

    @moderation_docs.resolve_protest_schema
    @action(methods=["patch"], detail=True)
    def resolve(self, request, pk=None):
        """Admin xử lý một kháng nghị (chấp thuận hoặc từ chối)."""
        protest_to_resolve = self.get_object()

        # 1. Lấy dữ liệu từ request
        new_status = request.data.get("status")
        note = request.data.get("resolution_note")

        # 2. Gọi hàm service để thực hiện logic nghiệp vụ
        try:
            resolved_protest = moderation_services.resolve_protest(
                protest=protest_to_resolve, admin_user=request.user, new_status=new_status, note=note
            )
        except moderation_services.ProtestResolutionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Ghi log lỗi ở đây
            return Response({"error": "Đã có lỗi hệ thống xảy ra."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Serialize kết quả và trả về response
        serializer = self.get_serializer(resolved_protest)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserModerationViewSet(viewsets.ViewSet):
    """
    ViewSet dành cho Admin để thực hiện các hành động kiểm duyệt trên người dùng.
    URL: /api/moderation/users/{user_id}/<action>/
    """
    permission_classes = [perms.IsAdmin]
    lookup_field = 'pk' # Dùng ID gốc của user để tra cứu

    def get_queryset(self):
        # Chỉ làm việc với các user không phải là superuser
        return User.objects.filter(is_superuser=False)

    def get_object(self):
        """Hàm helper để lấy đối tượng user hoặc báo lỗi 404."""
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs[self.lookup_field])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(methods=["patch"], detail=True, url_path="toggle-activation")
    def toggle_activation(self, request, pk=None):
        """
        Kích hoạt hoặc vô hiệu hóa một tài khoản người dùng.
        Đây chính là logic của hàm disable_account cũ.
        """
        user_to_toggle = self.get_object()
        try:
            # Gọi lại service đã có sẵn trong app users
            new_status = accounts_services.disable_user_account(
                admin_user=request.user,
                user_to_disable=user_to_toggle
            )
            status_text = "kích hoạt" if new_status else "vô hiệu hóa"
            return Response(
                {"message": f"Đã {status_text} tài khoản '{user_to_toggle.username}'."},
                status=status.HTTP_200_OK
            )
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)