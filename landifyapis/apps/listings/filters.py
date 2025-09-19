# apps/listings/filters.py
import django_filters
from django.db.models import Q
from functools import partial, reduce
import operator

from .models import Listing
from ..properties.models import Direction

# ==============================================================================
# == BỘ LỌC CHÍNH
# ==============================================================================

class ListingFilter(django_filters.FilterSet):
    """
    Bộ lọc tùy chỉnh cho model Listing.
    """
    # 1. Lọc theo từ khóa chung (tìm kiếm trong nhiều trường)
    q = django_filters.CharFilter(method='filter_by_keyword', label="Search Keyword")

    # 2. Lọc theo địa chỉ (sử dụng code)
    city_code = django_filters.CharFilter(field_name='property__location__ward__parent_code__parent_code__code')
    district_code = django_filters.CharFilter(field_name='property__location__ward__parent_code__code')
    ward_code = django_filters.CharFilter(field_name='property__location__ward__code')

    # 3. Lọc theo loại BĐS (sử dụng code)
    property_type_code = django_filters.CharFilter(method='filter_by_multiple_codes')

    # 4. Lọc theo khoảng giá và diện tích
    min_price = django_filters.NumberFilter(field_name="price_value", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price_value", lookup_expr='lte')
    min_area = django_filters.NumberFilter(field_name="property__area", lookup_expr='gte')
    max_area = django_filters.NumberFilter(field_name="property__area", lookup_expr='lte')

    #amenities = django_filters.CharFilter(method='filter_by_amenities', label="Lọc theo nhiều tiện ích")

    class Meta:
        model = Listing
        # Các trường có thể lọc trực tiếp (nếu cần)
        fields = ['listing_type__code']

    def filter_by_keyword(self, queryset, name, value):
        keywords = [kw.strip() for kw in value.split(',') if kw.strip()]
        if not keywords:
            return queryset

        queries = []

        for keyword in keywords:
            queries.append(
                Q(title__icontains=keyword) |
                Q(content__icontains=keyword) |
                Q(property__location__street__icontains=keyword) |
                Q(property__location__ward__name__icontains=keyword) |
                Q(property__location__ward__parent_code__name__icontains=keyword)
            )

        combined_query = reduce(operator.and_, queries)
        return queryset.filter(combined_query).distinct()


    def filter_by_multiple_codes(self, queryset, name, value):
        codes = [code.strip() for code in value.split(',') if code.strip()]
        if not codes:
            return queryset
        return queryset.filter(property__property_type__code__in=codes)

    def filter_by_direction(self, queryset, name, value):
        direction_codes = [code.strip() for code in value.split(',') if code.strip()]
        if not direction_codes:
            return queryset

        # Lấy ID của các hướng
        direction_ids = list(Direction.objects.filter(code__in=direction_codes).values_list('id', flat=True))
        if not direction_ids:
            return queryset.none()

        return queryset.filter(
            feature_values__feature__code='BALCONY_DIRECTION',  # Hoặc 'DIRECTION' tùy bạn quy ước
            feature_values__value__in=direction_ids
        ).distinct()

    def filter_by_amenities(self, queryset, name, value):
        """
        Lọc các tin đăng phải có TẤT CẢ các tiện ích được chỉ định.
        Frontend sẽ gửi lên một chuỗi các `code` được ngăn cách bởi dấu phẩy.
        Ví dụ: ?amenities=HAS_POOL,HAS_GYM,NEAR_SCHOOL
        """
        if not value:
            return queryset

        # Tách chuỗi thành một danh sách các code
        amenity_codes = [code.strip() for code in value.split(',')]

        # Với mỗi code, chúng ta lọc ra các tin đăng có feature đó và giá trị là True
        for code in amenity_codes:
            queryset = queryset.filter(
                feature_values__feature__code=code,
                feature_values__value=True  # JSONField có thể so sánh trực tiếp với boolean
            )

        # Dùng distinct() để đảm bảo không có kết quả trùng lặp
        return queryset.distinct()