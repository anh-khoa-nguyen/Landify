from django.urls import include, path
from rest_framework_nested import routers

from apps.interactions.views import ReviewViewSet

from . import views

# from django.views.decorators.cache import cache_page


router = routers.DefaultRouter()
router.register("listings", views.ListingViewSet, basename="listing")

listings_router = routers.NestedDefaultRouter(router, r"listings", lookup="public_id")
listings_router.register(r"reviews", ReviewViewSet, basename="listing-review")

# === TÍNH TOÁN THỜI GIAN CACHE (tính bằng giây) ===
# Cache trong 1 giờ = 60 phút * 60 giây
ONE_HOUR = 60 * 60
# ===============================================

urlpatterns = [
    path("listings/options/", views.ListingOptionsView.as_view(), name="listing-options"),
    # path('listings/creation-options/', cache_page(ONE_HOUR)(views.ListingCreationOptionsView.as_view()), name='listing-creation-options'),
    path("", include(router.urls)),
    path("", include(listings_router.urls)),
]
