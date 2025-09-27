from django.urls import path, include
from rest_framework_nested import routers

from . import views

router = routers.DefaultRouter()
router.register(r'properties', views.PropertyViewSet, basename='property')

properties_router = routers.NestedDefaultRouter(router, r'properties', lookup='property')
properties_router.register(r'media', views.MediaViewSet, basename='property-media')

urlpatterns = [
    # Bao gồm các URL từ cả hai router
    path('', include(router.urls)),
    path('', include(properties_router.urls)),
]