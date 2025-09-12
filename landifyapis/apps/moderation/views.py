from rest_framework import generics, parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common import perms
from apps.common.docs import moderation_docs

from .models import Protest, Report, User
from .serializers import ProtestSerializer, ReportSerializer
from . import services as moderation_services

# =================== REPORT & PROTEST (ADMINISTRATION) ==========================

@moderation_docs.report_viewset_schema
class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet để người dùng tạo báo cáo và admin quản lý."""

    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [perms.IsAdmin()]  # Chỉ admin mới được xem, sửa, xóa báo cáo

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return self.queryset
        return self.queryset.filter(reporter=user)  # Người dùng chỉ xem báo cáo của mình

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

@moderation_docs.protest_viewset_schema
class ProtestViewSet(viewsets.ModelViewSet):
    """ViewSet chỉ dành cho Admin để quản lý và xử lý các kháng nghị."""

    queryset = Protest.objects.select_related("protester", "listing", "admin").all()
    serializer_class = ProtestSerializer
    permission_classes = [perms.IsAdmin]  # Chỉ admin mới được truy cập

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
