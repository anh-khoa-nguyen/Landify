from django.urls import path, include
from rest_framework_nested import routers
from apps.interactions.views import ReviewViewSet
from . import views

router = routers.DefaultRouter()
router.register("listings", views.ListingViewSet, basename="listing")

listings_router = routers.NestedDefaultRouter(router, r'listings', lookup='public_id')
listings_router.register(r'reviews', ReviewViewSet, basename='listing-review')

urlpatterns = [
    path('listings/creation-options/', views.ListingCreationOptionsView.as_view(), name='listing-creation-options'),
    path('listings/filter-options/', views.ListingFilterOptionsView.as_view(), name='listing-filter-options'),
    path('', include(router.urls)),
    path('', include(listings_router.urls)),
]