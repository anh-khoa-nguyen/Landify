from django.urls import path, include, re_path
# from rest_framework import routers
from rest_framework_nested import routers
from landifys import views

r = routers.DefaultRouter()
r.register('users', views.UserViewSet, basename='user')
r.register('lists', views.ListingViewSet, basename='listing')
r.register('reports', views.ReportViewSet, basename='report')
r.register('appointments', views.AppointmentViewSet, basename='appointment')
r.register('wishlists', views.WishlistViewSet, basename='wishlist')
r.register('auth', views.AuthVerificationView, basename='auth')
r.register('properties-analysis', views.PropertyAnalysisViewSet, basename='property-analysis')
r.register('properties', views.PropertyViewSet, basename='property')
r.register('media', views.MediaViewSet, basename='media')
r.register('posts', views.PostViewSet, basename='post')
r.register('comments', views.CommentViewSet, basename='comment')
r.register('protests', views.ProtestViewSet, basename='protest')

posts_router = routers.NestedDefaultRouter(r, 'posts', lookup='post')
posts_router.register('comments', views.CommentViewSet, basename='post-comments')

properties_router = routers.NestedDefaultRouter(r, 'properties', lookup='property')
properties_router.register('media', views.MediaViewSet, basename='property-media')

urlpatterns = [
    path('', include(r.urls)),
    path('', include(posts_router.urls)),
    path('', include(properties_router.urls)),
    # path('', views.index),
    re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
]
