# apps/common/tasks/prices.py
from celery import shared_task
from django.db.models import Avg, Count
from collections import defaultdict
import logging

from apps.listings.models import Listing, ListingType, UnitPrice
from apps.common.models import GeoGridStatistic
from apps.common.utils.geogrid import geogrid_converter

logger = logging.getLogger(__name__)


@shared_task(name="prices.update_geogrid_statistics")
def update_geogrid_statistics():
    logger.info("Bắt đầu tác vụ: Cập nhật thống kê giá theo lưới địa lý...")

    try:
        rent_type = ListingType.objects.get(code='RENT')
        sell_type = ListingType.objects.get(code='BUY_SELL')
        per_m2_unit = UnitPrice.objects.get(code='PER_M2')
    except Exception as e:
        logger.error(f"LỖI: Không thể tải dữ liệu gốc: {e}. Dừng tác vụ.")
        return

    # 1. Lấy tất cả tin đăng có tọa độ và giá
    listings_with_coords = Listing.objects.filter(
        active=True,
        property__location__point__isnull=False,
        price_value__isnull=False
    ).select_related(
        'listing_type',
        'property__property_type',  # Thêm property_type vào select_related
        'unit_price',
        'property__location'
    ).values(
        'price_value',
        'listing_type__code',  # Truy vấn trực tiếp từ listing_type
        # 'property__property_type__code' # Không cần lấy ở đây, sẽ xử lý sau
        'unit_price__code',
        'property__location__point'
    )

    # 2. Nhóm các tin đăng vào các ô lưới trong bộ nhớ
    grid_data = defaultdict(lambda: {'rent_prices': [], 'sell_prices_m2': []})
    for listing in listings_with_coords:
        point = listing['property__location__point']
        cell_id = geogrid_converter.get_cell_id(point.y, point.x)
        if not cell_id:
            continue

        listing_type_code = listing['listing_type__code']
        unit_price_code = listing['unit_price__code']

        if listing_type_code == 'RENT':
            grid_data[cell_id]['rent_prices'].append(float(listing['price_value']))
        elif listing_type_code == 'BUY_SELL' and unit_price_code == 'PER_M2':
            grid_data[cell_id]['sell_prices_m2'].append(float(listing['price_value']))

    # 3. Tính toán và chuẩn bị để cập nhật CSDL
    stats_to_update = []
    for cell_id, data in grid_data.items():
        center_lat, center_lng = geogrid_converter.get_cell_center(cell_id)

        avg_rent = sum(data['rent_prices']) / len(data['rent_prices']) if data['rent_prices'] else None
        avg_sell = sum(data['sell_prices_m2']) / len(data['sell_prices_m2']) if data['sell_prices_m2'] else None

        stats_to_update.append(
            GeoGridStatistic(
                grid_cell_id=cell_id,
                center_lat=center_lat,
                center_lng=center_lng,
                avg_rent_price=avg_rent,
                rent_listing_count=len(data['rent_prices']),
                avg_sell_price_per_m2=avg_sell,
                sell_listing_count=len(data['sell_prices_m2']),
            )
        )

    # 4. Cập nhật CSDL một cách hiệu quả
    if stats_to_update:
        GeoGridStatistic.objects.bulk_update_or_create(
            stats_to_update,
            ['avg_rent_price', 'rent_listing_count', 'avg_sell_price_per_m2', 'sell_listing_count', 'center_lat',
             'center_lng', 'last_updated'],
            match_field='grid_cell_id'
        )

    logger.info(f"Hoàn tất. Đã cập nhật thống kê cho {len(stats_to_update)} ô lưới.")