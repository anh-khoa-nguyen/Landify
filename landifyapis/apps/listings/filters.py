# apps/listings/filters.py
import operator
from functools import partial, reduce

import django_filters
from django.db.models import Q

from ..properties.models import Direction
from .models import Listing, PropertyFeature

# ==============================================================================
# == BỘ LỌC CHÍNH
# ==============================================================================

class FeatureFilter(django_filters.Filter):
    def filter(self, qs, value):
        # Chúng ta sẽ lấy dữ liệu từ request.query_params
        if not hasattr(self.parent.request, 'query_params'):
            return qs

        query_params = self.parent.request.query_params

        # --- Bắt đầu sao chép logic từ ListingViewSet.filter_queryset ---
        feature_params = {}
        for key in query_params:
            if key.startswith('features__'):
                parts = key.split('__')
                if len(parts) == 3:
                    feature_params[parts[1]] = None

        if not feature_params:
            return qs

        features_map = {
            f.code: f.feature_type
            for f in PropertyFeature.objects.filter(code__in=feature_params.keys())
        }

        for key, val in query_params.items():
            if key.startswith('features__'):
                parts = key.split('__')
                if len(parts) == 3:
                    feature_code, lookup_expr = parts[1], parts[2]
                    feature_type = features_map.get(feature_code)
                    if not feature_type:
                        continue

                    processed_value = val
                    if feature_type == PropertyFeature.FeatureType.BOOLEAN:
                        processed_value = val.lower() == 'true'
                    elif feature_type == PropertyFeature.FeatureType.FLOAT:
                        try:
                            processed_value = float(val)
                        except (ValueError, TypeError):
                            return qs.none()

                    q_object = Q(
                        feature_values__feature__code=feature_code,
                        **{f'feature_values__value__{lookup_expr}': processed_value}
                    )
                    qs = qs.filter(q_object)

        return qs.distinct()

class ListingFilter(django_filters.FilterSet):
    """
    Bộ lọc tùy chỉnh cho model Listing.
    """

    # 1. Lọc theo từ khóa chung (tìm kiếm trong nhiều trường)
    q = django_filters.CharFilter(method="filter_by_keyword", label="Search Keyword")

    # 2. Lọc theo địa chỉ (sử dụng code)
    city_code = django_filters.CharFilter(field_name="property__location__ward__parent_code__parent_code__code")
    district_code = django_filters.CharFilter(field_name="property__location__ward__parent_code__code")
    ward_code = django_filters.CharFilter(field_name="property__location__ward__code")

    # 3. Lọc theo loại BĐS (sử dụng code)
    property_type_code = django_filters.CharFilter(method="filter_by_multiple_codes")

    # 4. Lọc theo khoảng giá và diện tích
    min_price = django_filters.NumberFilter(field_name="price_value", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price_value", lookup_expr="lte")
    min_area = django_filters.NumberFilter(field_name="property__area", lookup_expr="gte")
    max_area = django_filters.NumberFilter(field_name="property__area", lookup_expr="lte")

    listing_type_code = django_filters.CharFilter(
        field_name="listing_category__listing_type__code", label="Lọc theo mã loại tin đăng (BUY_SELL, RENT)"
    )

    features = FeatureFilter()

    class Meta:
        model = Listing
        # Các trường có thể lọc trực tiếp (nếu cần)
        fields = []

    def filter_by_keyword(self, queryset, name, value):
        keywords = [kw.strip() for kw in value.split(",") if kw.strip()]
        if not keywords:
            return queryset

        queries = []

        for keyword in keywords:
            queries.append(
                Q(title__icontains=keyword)
                | Q(content__icontains=keyword)
                | Q(property__location__street__icontains=keyword)
                | Q(property__location__ward__name__icontains=keyword)
                | Q(property__location__ward__parent_code__name__icontains=keyword)
            )

        combined_query = reduce(operator.and_, queries)
        return queryset.filter(combined_query).distinct()

    def filter_by_multiple_codes(self, queryset, name, value):
        codes = [code.strip() for code in value.split(",") if code.strip()]
        if not codes:
            return queryset
        return queryset.filter(listing_category__property_type__code__in=codes)

    def filter_by_direction(self, queryset, name, value):
        direction_codes = [code.strip() for code in value.split(",") if code.strip()]
        if not direction_codes:
            return queryset

        # Lấy ID của các hướng
        direction_ids = list(Direction.objects.filter(code__in=direction_codes).values_list("id", flat=True))
        if not direction_ids:
            return queryset.none()

        return queryset.filter(
            feature_values__feature__code="BALCONY_DIRECTION",  # Hoặc 'DIRECTION' tùy bạn quy ước
            feature_values__value__in=direction_ids,
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
        amenity_codes = [code.strip() for code in value.split(",")]

        # Với mỗi code, chúng ta lọc ra các tin đăng có feature đó và giá trị là True
        for code in amenity_codes:
            queryset = queryset.filter(
                feature_values__feature__code=code,
                feature_values__value=True,  # JSONField có thể so sánh trực tiếp với boolean
            )

        # Dùng distinct() để đảm bảo không có kết quả trùng lặp
        return queryset.distinct()
