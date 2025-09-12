# apps/common/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import SiteStatistic

class HomepageStatsView(APIView):
    """
    API View để trả về các số liệu thống kê chung cho trang chủ.
    Dữ liệu này được tính toán trước nên truy vấn rất nhanh.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        try:
            # Lấy giá trị từ model
            total_listings = SiteStatistic.objects.get(key='total_active_listings').value
        except SiteStatistic.DoesNotExist:
            # Trả về 0 nếu chưa có dữ liệu
            total_listings = 0

        # Định dạng số theo kiểu có dấu phẩy/chấm
        formatted_total = f"{total_listings:,}".replace(",", ".")

        data = {
            'total_listings': total_listings,
            'formatted_total_listings': f"{formatted_total} bất động sản"
        }
        return Response(data)