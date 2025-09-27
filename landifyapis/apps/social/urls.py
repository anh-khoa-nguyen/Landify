from django.urls import path, include
from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register("posts", views.PostViewSet, basename="post")

posts_router = routers.NestedDefaultRouter(router, "posts", lookup="post")
posts_router.register("comments", views.CommentViewSet, basename="post-comment")

urlpatterns = [
    path('', include(router.urls)),
    path('', include(posts_router.urls)),
]