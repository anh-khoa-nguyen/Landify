# apps/common/urls.py
from django.urls import path

from .views import HomepageStatsView, CityListView, DistrictListView, WardListView

urlpatterns = [
    path("homepage-stats/", HomepageStatsView.as_view(), name="homepage-stats"),

    path("address/cities/", CityListView.as_view(), name="custom-city-list"),
    path("address/districts/", DistrictListView.as_view(), name="custom-district-list"),
    path("address/wards/", WardListView.as_view(), name="custom-ward-list"),
]
