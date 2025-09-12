# landifyapis/celery.py

import os

from celery import Celery

# Đặt biến môi trường mặc định cho settings của Django
# để Celery biết cách tìm dự án Django.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "landifyapis.settings")

# Tạo một instance của ứng dụng Celery, đặt tên theo thư mục dự án
app = Celery("landifyapis")

# Nạp cấu hình từ file settings.py của Django.
# namespace='CELERY' nghĩa là tất cả các config của Celery trong settings.py
# phải bắt đầu bằng 'CELERY_', ví dụ: CELERY_BROKER_URL.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Tự động tìm tất cả các file tasks.py trong các app đã đăng ký trong INSTALLED_APPS.
# Celery sẽ tự động đăng ký các tác vụ được định nghĩa trong các file đó.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
