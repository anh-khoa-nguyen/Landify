# apps/common/urls.py
from django.urls import path
from .views import HomepageStatsView

urlpatterns = [
    path('homepage-stats/', HomepageStatsView.as_view(), name='homepage-stats'),
]