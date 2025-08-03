import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landifyapis.settings')

# Tạo một instance của ứng dụng Celery
app = Celery('landifyapis')

# Nạp cấu hình từ file settings.py của Django.
# namespace='CELERY' nghĩa là tất cả các config của Celery trong settings.py phải bắt đầu bằng 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tự động tìm tất cả các file tasks.py trong các app đã đăng ký.
app.autodiscover_tasks()