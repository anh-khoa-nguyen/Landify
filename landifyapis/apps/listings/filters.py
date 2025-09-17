# apps/listings/filters.py
import django_filters
from django.db.models import Q
from functools import partial

from .models import Listing

def filter_by_feature_exact(queryset, name, value, feature_code):
    processed_value = float(value)

    return queryset.filter(
        feature_values__feature__code=feature_code,
        feature_values__value__exact=processed_value
    ).distinct()

def filter_by_feature_range(queryset, name, value, feature_code, lookup_expr):
    """Lọc các tin đăng có feature với giá trị trong một khoảng (gte, lte)."""
    # Chuyển đổi giá trị sang float để so sánh số
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        return queryset.none() # Trả về rỗng nếu giá trị không phải là số

    filter_kwargs = {
        f'feature_values__feature__code': feature_code,
        f'feature_values__value__{lookup_expr}': numeric_value
    }
    return queryset.filter(**filter_kwargs).distinct()

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
    property_type_code = django_filters.CharFilter(field_name='property__property_type__code')

    # 4. Lọc theo khoảng giá và diện tích
    min_price = django_filters.NumberFilter(field_name="price_value", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price_value", lookup_expr='lte')
    min_area = django_filters.NumberFilter(field_name="property__area", lookup_expr='gte')
    max_area = django_filters.NumberFilter(field_name="property__area", lookup_expr='lte')

    # 5. Lọc theo các đặc điểm (features) - Đây là phần phức tạp nhất
    beds = django_filters.NumberFilter(
        method=partial(filter_by_feature_exact, feature_code='NUM_BEDROOMS'),
        label="Số phòng ngủ"
    )
    baths = django_filters.NumberFilter(
        method=partial(filter_by_feature_exact, feature_code='NUM_BATHROOMS'),
        label="Số phòng tắm"
    )

    direction_code = django_filters.CharFilter(method='filter_by_direction', label="Hướng nhà")
    amenities = django_filters.CharFilter(method='filter_by_amenities', label="Lọc theo nhiều tiện ích")

    # --- Bộ lọc cho CHO THUÊ (thay thế RentalDetail) ---
    min_deposit = django_filters.NumberFilter(
        method=partial(filter_by_feature_range, feature_code='DEPOSIT_AMOUNT', lookup_expr='gte'),
        label="Tiền cọc tối thiểu"
    )
    max_deposit = django_filters.NumberFilter(
        method=partial(filter_by_feature_range, feature_code='DEPOSIT_AMOUNT', lookup_expr='lte'),
        label="Tiền cọc tối đa"
    )
    min_lease = django_filters.NumberFilter(
        method=partial(filter_by_feature_range, feature_code='MIN_LEASE_DURATION', lookup_expr='gte'),
        label="Thời hạn thuê tối thiểu (tháng)"
    )
    allow_pets = django_filters.BooleanFilter(
        method=partial(filter_by_feature_exact, feature_code='ALLOW_PETS'),
        label="Cho phép thú cưng"
    )

    # --- Bộ lọc cho MUA BÁN (thay thế BuySellDetail) ---
    is_mortgaged = django_filters.BooleanFilter(
        method=partial(filter_by_feature_exact, feature_code='IS_MORTGAGED'),
        label="Đang thế chấp"
    )
    condition_status = django_filters.CharFilter(
        method=partial(filter_by_feature_exact, feature_code='CONDITION_STATUS'),
        label="Tình trạng nhà"
    )

    class Meta:
        model = Listing
        # Các trường có thể lọc trực tiếp (nếu cần)
        fields = ['listing_type__code']

    def filter_by_keyword(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(content__icontains=value) |
            Q(property__location__street__icontains=value) |
            Q(property__location__ward__name__icontains=value) |
            Q(property__location__ward__parent_code__name__icontains=value)
        ).distinct()

    def filter_by_direction(self, queryset, name, value):
        # Lọc các tin đăng có feature 'Hướng nhà' với giá trị là ID của Direction
        # Giả sử `value` truyền vào là `code` của Direction, ví dụ: 'EAST'
        from apps.properties.models import Direction
        try:
            direction_id = Direction.objects.get(code=value).id
            return queryset.filter(
                feature_values__feature__code='BALCONY_DIRECTION',
                feature_values__value__exact=direction_id
            ).distinct()
        except Direction.DoesNotExist:
            return queryset.none()

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