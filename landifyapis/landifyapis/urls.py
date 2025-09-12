# landifyapis/urls.py

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
TokenObtainPairView,
TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('apps.users.urls')),
    path('', include('apps.properties.urls')),
    path('', include('apps.listings.urls')),
    path('', include('apps.social.urls')),
    path('', include('apps.interactions.urls')),
    path('', include('apps.moderation.urls')),
    path('', include('apps.verification.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/', include('apps.users.urls')),
    path('api/', include('apps.listings.urls')),
    path('api/', include('apps.properties.urls')),
    path('api/', include('apps.social.urls')),
    path('api/', include('apps.interactions.urls')),
    path('api/', include('apps.moderation.urls')),
    path('api/', include('apps.verification.urls')),

    path("api/address/", include("vi_address.urls")),
    path('api/common/', include('apps.common.urls')),  # <-- THÊM DÒNG NÀY

    # URL cho giao diện Redoc
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
