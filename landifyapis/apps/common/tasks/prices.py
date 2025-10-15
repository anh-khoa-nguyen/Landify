# apps/common/tasks/prices.py
import logging
from collections import defaultdict

from celery import shared_task
from django.db.models import Avg, Count

from apps.common.models import GeoGridStatistic
from apps.common.utils.geogrid import geogrid_converter
from apps.listings.models import Listing, ListingType, UnitPrice

logger = logging.getLogger(__name__)


@shared_task(name="prices.update_geogrid_statistics")
def update_geogrid_statistics():
    logger.info("Bắt đầu tác vụ: Cập nhật thống kê giá theo lưới địa lý...")

    # 1. Lấy tất cả tin đăng có đủ thông tin cần thiết
    listings_with_data = (
        Listing.objects.filter(
            active=True,
            property__location__point__isnull=False,
            price_value__isnull=False,
            listing_category__isnull=False,  # Chỉ lấy các tin có category
            unit_price__isnull=False,  # Chỉ lấy các tin có đơn vị giá
        )
        .select_related(
            "listing_category__listing_type", "listing_category__property_type", "unit_price", "property__location"
        )
        .values(
            "price_value",
            "listing_category_id",
            "listing_category__listing_type__code",
            "listing_category__property_type__code",
            "unit_price__code",
            "property__location__point",
        )
    )

    # 2. Nhóm các tin đăng vào các ô lưới trong bộ nhớ
    grid_data = defaultdict(
        lambda: defaultdict(
            lambda: {
                "prices": [],
                "listing_type_code": None,
                "property_type_code": None,
            }
        )
    )

    for listing in listings_with_data:
        point = listing["property__location__point"]
        cell_id = geogrid_converter.get_cell_id(point.y, point.x)
        if not cell_id:
            continue

        category_id = listing["listing_category_id"]
        unit_price_code = listing["unit_price__code"]

        # Chỉ xử lý các tin "Cho thuê" hoặc "Mua bán" có giá /m²
        if listing["listing_category__listing_type__code"] == "RENT" or (
            listing["listing_category__listing_type__code"] == "BUY_SELL" and unit_price_code == "PER_M2"
        ):
            grid_data[cell_id][category_id]["prices"].append(float(listing["price_value"]))
            if not grid_data[cell_id][category_id]["listing_type_code"]:
                grid_data[cell_id][category_id]["listing_type_code"] = listing["listing_category__listing_type__code"]
                grid_data[cell_id][category_id]["property_type_code"] = listing[
                    "listing_category__property_type__code"
                ]

    """
    grid_data = {
        'cell_10.77_106.70': {  # Đây là một cell_id
            '27': {  # Đây là một category_id
                'prices': [25000000.0, 26000000.0, 24500000.0],
                'listing_type_code': 'RENT',
                'property_type_code': 'APARTMENT'
            },
            '15': { # Một category_id khác trong cùng cell
                'prices': [65000000.0, 68000000.0],
                'listing_type_code': 'BUY_SELL',
                'property_type_code': 'LAND'
            }
        },
        'cell_10.78_106.71': { # Một cell_id khác
            # ... dữ liệu của ô lưới khác ...
        }
    }
    """

    # 3. Tính toán và chuẩn bị để cập nhật CSDL
    stats_to_update = []
    for cell_id, categories in grid_data.items():
        center_lat, center_lng = geogrid_converter.get_cell_center(cell_id)

        stats_payload = {}
        for category_id, data in categories.items():
            if data["prices"]:
                avg_price = sum(data["prices"]) / len(data["prices"])

                # Tạo key là string để tương thích JSON
                category_key = str(category_id)

                stats_payload[category_key] = {
                    "avg_price": avg_price,
                    "count": len(data["prices"]),
                    "listing_type_code": data["listing_type_code"],
                    "property_type_code": data["property_type_code"],
                }

        if stats_payload:  # Chỉ thêm vào danh sách nếu có dữ liệu để cập nhật
            stats_to_update.append(
                GeoGridStatistic(
                    grid_cell_id=cell_id, center_lat=center_lat, center_lng=center_lng, stats_by_category=stats_payload
                )
            )

    # 4. Cập nhật CSDL một cách hiệu quả
    if stats_to_update:
        GeoGridStatistic.objects.bulk_update_or_create(
            stats_to_update,
            # Chỉ cần cập nhật các trường này
            ["stats_by_category", "center_lat", "center_lng"],
            match_field="grid_cell_id",
        )

    logger.info(f"Hoàn tất. Đã cập nhật thống kê cho {len(stats_to_update)} ô lưới.")
