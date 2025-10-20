from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import parsers, permissions, serializers, status, viewsets
from rest_framework.response import Response

from apps.common import perms
from apps.common.docs import listings_docs, media_docs
from apps.common.services import BusinessLogicError

from . import services as property_services
from .models import Property, PropertyMedia
from .serializers import PropertyMediaSerializer, PropertySerializer


# ==============================================================================
# PRIMARY PROPERTY VIEWSET
# ==============================================================================
# ViewSet chính quản lý các tài nguyên Bất động sản (Property).
# Đây là endpoint gốc cho các hoạt động CRUD trên Property.
class PropertyViewSet(viewsets.ModelViewSet):
    """ViewSet để quản lý Bất động sản (thông tin vật lý)."""

    queryset = (
        Property.objects.select_related("owner", "location", "property_type")
        .prefetch_related("media")
        .filter(active=True)
    )

    serializer_class = PropertySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [perms.IsIdentityVerified()]
        return [perms.IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        serializer.save()


# ==============================================================================
# NESTED MEDIA VIEWSET
# ==============================================================================
# ViewSet lồng nhau để quản lý Media (ảnh/video) của một Property cụ thể.
# URL: /api/properties/{property_pk}/media/
@media_docs.media_viewset_schema
class MediaViewSet(viewsets.ModelViewSet):
    """
    ViewSet để quản lý Media (ảnh/video), lồng trong một Property.
    URL: /api/properties/{property_pk}/media/
    """

    queryset = PropertyMedia.objects.all()
    serializer_class = PropertyMediaSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return self.queryset.filter(property_id=self.kwargs.get("property_pk"))

    def create(self, request, *args, **kwargs):
        """
        Xử lý việc upload nhiều file media cùng lúc bằng cách gán trực tiếp
        vào CloudinaryField.
        """
        prop = get_object_or_404(Property, pk=self.kwargs.get("property_pk"))

        if prop.owner != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Bạn không có quyền thêm media cho bất động sản này."},
                status=status.HTTP_403_FORBIDDEN
            )

        media_files = request.FILES.getlist("files")

        if not media_files:
            return Response(
                {"files": "Vui lòng cung cấp ít nhất một file với key là 'files'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            created_media_instances = property_services.add_multiple_media_to_property(
                prop=prop,
                media_files=media_files
            )
        except BusinessLogicError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = self.get_serializer(created_media_instances, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Ghi đè logic xóa để kiểm tra quyền sở hữu của Bất động sản cha.
        """
        media_object = self.get_object()
        parent_property = media_object.property

        if parent_property.owner != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Bạn không có quyền xóa media của bất động sản này."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)
