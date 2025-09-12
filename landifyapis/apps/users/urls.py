from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register("users", views.UserViewSet, basename="user")
router.register(r'auth', views.AuthViewSet, basename='auth')

urlpatterns = router.urls