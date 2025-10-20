# apps/common/views.py
from rest_framework import permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.gis.geos import Point

from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from vi_address import views as vi_address_views
from vi_address import models as vi_address_models
from vi_address import serializers as vi_address_serializers

from .models import SiteStatistic


class HomepageStatsView(APIView):
    """
    API View để trả về các số liệu thống kê chung cho trang chủ.
    Dữ liệu này được tính toán trước nên truy vấn rất nhanh.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        try:
            total_listings = SiteStatistic.objects.get(key="total_active_listings").value
        except SiteStatistic.DoesNotExist:
            total_listings = 0

        formatted_total = f"{total_listings:,}".replace(",", ".")

        data = {"total_listings": total_listings, "formatted_total_listings": f"{formatted_total} bất động sản"}
        return Response(data)

class CityListView(generics.ListAPIView):
    """
    API tùy chỉnh để lấy danh sách Tỉnh/Thành phố, có hỗ trợ tìm kiếm.
    """
    queryset = vi_address_models.City.objects.all()
    serializer_class = vi_address_serializers.CitySerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'name_with_type']
    # Pagination được áp dụng tự động từ settings.py

class DistrictListView(generics.ListAPIView):
    """
    API tùy chỉnh để lấy danh sách Quận/Huyện, có hỗ trợ lọc theo thành phố và tìm kiếm.
    """
    queryset = vi_address_models.District.objects.all()
    serializer_class = vi_address_serializers.DistrictSerializer # Giả sử serializer này tồn tại
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['parent_code'] # Cho phép lọc bằng ?parent_code=<city_id>
    search_fields = ['name', 'name_with_type']

class WardListView(generics.ListAPIView):
    """
    API tùy chỉnh để lấy danh sách Phường/Xã, có hỗ trợ lọc theo quận/huyện và tìm kiếm.
    """
    queryset = vi_address_models.Ward.objects.all()
    serializer_class = vi_address_serializers.WardSerializer # Giả sử serializer này tồn tại
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['parent_code'] # Cho phép lọc bằng ?parent_code=<district_id>
    search_fields = ['name', 'name_with_type']