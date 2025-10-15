from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register(r"verification", views.VerificationViewSet, basename="verification")
router.register(r"agora", views.AgoraTokenViewSet, basename="agora")

router.register(r"analysis", views.PropertyAnalysisViewSet, basename="analysis")

urlpatterns = router.urls
