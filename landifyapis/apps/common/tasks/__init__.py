#celery -A landifyapis worker -l info -P solo
#celery -A landifyapis beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
#from apps.common.tasks.prices import update_geogrid_statistics
# .delay() sẽ đưa task vào hàng đợi Redis ngay lập tức
#update_geogrid_statistics.delay()

from . import notifications, stats

__all__ = [
    "notifications",
    "stats",
    "prices",
]
