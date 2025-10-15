import logging

from celery import shared_task

from apps.common.models import SiteStatistic
from apps.listings.models import Listing

logger = logging.getLogger(__name__)


@shared_task(name="stats.update_total_listings_count")
def update_total_listings_count():
    """
    Đếm tổng số tin đăng đang hoạt động và lưu vào model SiteStatistic.
    Đây là một full recount để đảm bảo tính chính xác.
    """
    logger.info("Bắt đầu tác vụ: Cập nhật tổng số tin đăng...")
    try:
        # Thực hiện truy vấn đếm
        count = Listing.objects.filter(active=True, status=Listing.Status.AVAILABLE).count()

        # Sử dụng update_or_create để tạo mới nếu chưa có, hoặc cập nhật nếu đã có
        stat, created = SiteStatistic.objects.update_or_create(key="total_active_listings", defaults={"value": count})

        if created:
            logger.info(f"Đã tạo thống kê 'total_active_listings' với giá trị: {count}")
        else:
            logger.info(f"Đã cập nhật thống kê 'total_active_listings' thành: {count}")

    except Exception as e:
        logger.error(f"LỖI trong tác vụ update_total_listings_count: {e}", exc_info=True)
