# apps/listings/tasks/__init__.py

# Import các module task để Celery có thể "nhìn thấy" chúng
from . import moderation
from . import notifications

# (Tùy chọn) Định nghĩa __all__
__all__ = [
    "moderation",
    "notifications",
]