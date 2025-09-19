# landifyapis/settings.py

import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from celery.schedules import crontab

# PRODUCTION: celery -A landifyapis beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
CELERY_BEAT_SCHEDULE = {
    'update-listing-count-every-night': {
        'task': 'stats.update_total_listings_count', # Tên tác vụ đã đăng ký ở trên
        'schedule': crontab(hour=23, minute=0),      # Chạy vào 23:00 (11h đêm) mỗi ngày
    },
    'update-area-prices-every-3-hours': {
        'task': 'prices.update_geogrid_statistics',
        'schedule': crontab(minute=0, hour='*/3'),
    },
}

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

#sys.path.insert(0, str(BASE_DIR))

MEDIA_ROOT = "%s/landifys/static/" % BASE_DIR

# ==============================================================================
# CORE SETTINGS (Đọc từ .env)
# ==============================================================================
# Lấy SECRET_KEY từ biến môi trường
SECRET_KEY = os.getenv('SECRET_KEY')

# Lấy DEBUG mode. Cung cấp giá trị mặc định 'False' để an toàn hơn.
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# ALLOWED_HOSTS nên được cấu hình chặt chẽ hơn khi deploy
ALLOWED_HOSTS = ["*"] # Sẽ cần sửa lại khi deploy

# ==============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    "corsheaders",
    "channels",
    "django.contrib.gis",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # Cho phép vô hiệu hóa refresh token
    "cloudinary",
    "ckeditor",
    "ckeditor_uploader",
    "drf_spectacular",
    "vi_address",
    "django_celery_beat",
    "bulk_update_or_create",
    # === MY APPS ===
    'apps.common.apps.CommonConfig',
    'apps.users.apps.UsersConfig',
    'apps.properties.apps.PropertiesConfig',
    'apps.listings.apps.ListingsConfig',
    'apps.interactions.apps.InteractionsConfig',
    'apps.social.apps.SocialConfig',
    'apps.moderation.apps.ModerationConfig',
    'apps.verification.apps.VerificationConfig',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "landifyapis.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "landifyapis.wsgi.application"
ASGI_APPLICATION = "landifyapis.asgi.application"

# ==============================================================================
# DATABASE SETTINGS
# ==============================================================================
# Sử dụng PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": os.getenv('DB_ENGINE', 'django.contrib.gis.db.backends.postgis'),
        "NAME": os.getenv('DB_NAME'),
        "USER": os.getenv('DB_USER'),
        "PASSWORD": os.getenv('DB_PASSWORD'),
        "HOST": os.getenv('DB_HOST', 'localhost'),
        "PORT": os.getenv('DB_PORT', '5432'),
    },
    "legacy_mysql": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "du_an_ban_dat",  # Tên CSDL MySQL cũ
        "USER": "root",      # Thay bằng user của bạn
        "PASSWORD": "Abc@123",  # Thay bằng mật khẩu của bạn
        "HOST": "localhost",            # Hoặc IP của server MySQL
        "PORT": "3306",
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# ==============================================================================
# AUTHENTICATION & INTERNATIONALIZATION
# ==============================================================================
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC, MEDIA & CKEDITOR
# ==============================================================================
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_UPLOAD_PATH = "ckeditor/posts/"

# ==============================================================================
# DJANGO REST FRAMEWORK
# ==============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Ưu tiên kiểm tra token của Firebase trước
        "apps.common.authentication.FirebaseAuthentication",

        # Nếu không có token Firebase, nó sẽ kiểm tra token của Simple JWT
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Landify API',
    'DESCRIPTION': 'Tài liệu API chi tiết cho dự án Landify',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ==============================================================================
# THIRD-PARTY SERVICE CREDENTIALS (Đọc từ .env)
# ==============================================================================
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True,
)

FPT_AI_API_KEY = os.getenv('FPT_AI_API_KEY')

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

AGORA_APP_ID = os.getenv('AGORA_APP_ID')
AGORA_APP_CERTIFICATE = os.getenv('AGORA_APP_CERTIFICATE')

# ==============================================================================
# CELERY & REDIS (Đọc từ .env)
# ==============================================================================
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
print(REDIS_PASSWORD)
# Cấu hình Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}",  # Dùng DB số 1 cho cache để tách biệt với Celery
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Cấu hình Celery
CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
CELERY_RESULT_BACKEND = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_POOL_LIMIT = 10  # Giới hạn số kết nối trong pool của broker
CELERY_REDIS_MAX_CONNECTIONS = 10 # Giới hạn tổng số kết nối cho Redis
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

MOMO_PARTNER_CODE = os.getenv('MOMO_PARTNER_CODE')
MOMO_ACCESS_KEY = os.getenv('MOMO_ACCESS_KEY')
MOMO_SECRET_KEY = os.getenv('MOMO_SECRET_KEY')
MOMO_REDIRECT_URL = os.getenv('MOMO_REDIRECT_URL')
MOMO_IPN_URL_BASE = os.getenv('MOMO_IPN_URL_BASE')

# ==============================================================================
# DJANGO CHANNELS
# ==============================================================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"],
        },
    },
}

# ==============================================================================
# GEO DJANGO SETTINGS (Thêm vào cuối file)
# ==============================================================================
# Cung cấp đường dẫn tường minh đến thư viện GDAL đã được cài đặt bởi OSGeo4W.
# Điều này giúp Django tìm thấy thư viện mà không cần phụ thuộc vào biến môi trường PATH.
#
# QUAN TRỌNG:
# 1. Sử dụng chuỗi thô (raw string) bằng cách thêm chữ 'r' ở đầu.
# 2. Thay thế 'gdal309.dll' bằng TÊN FILE CHÍNH XÁC bạn đã tìm thấy ở Bước 1.

GDAL_LIBRARY_PATH = r'D:\Backend\Landify\landifyapis\.venv\Lib\site-packages\osgeo\gdal.dll'

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # Định dạng của một dòng log: Mức độ - Thời gian - Tên module - Nội dung
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',  # Chỉ ghi các log từ mức WARNING, ERROR, CRITICAL vào file
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log', # File log sẽ nằm ở thư mục gốc của dự án
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',  # Hiển thị các log từ mức INFO trở lên ra console
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        # Áp dụng 2 handler này cho toàn bộ dự án
        'handlers': ['console', 'file'],
        'level': 'INFO', # Mức log tối thiểu để được xử lý
    },
}

GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
GOOGLE_APPLICATION_CREDENTIALS = str(BASE_DIR / GOOGLE_CREDENTIALS_FILE)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# ==============================================================================
# CORS (CROSS-ORIGIN RESOURCE SHARING) SETTINGS
# ==============================================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend Next.js của bạn
    "http://127.0.0.1:3000", # Thêm cả địa chỉ này cho chắc chắn
    "http://192.168.137.1:3000",  # Thêm cả địa chỉ này cho chắc chắn
]

# (Tùy chọn) Nếu bạn cần gửi cookie hoặc header Authorization
CORS_ALLOW_CREDENTIALS = True