from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register(r"reports", views.ReportViewSet, basename="report")
router.register(r"protests", views.ProtestViewSet, basename="protest")

urlpatterns = router.urls
