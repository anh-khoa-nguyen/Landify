# landifyapis/__init__.py

# Dòng này đảm bảo rằng app Celery được import khi Django khởi động
# để decorator @shared_task có thể sử dụng app đó.
from .celery import app as celery_app

__all__ = ("celery_app",)
