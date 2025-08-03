from django.urls import path, include, re_path
from rest_framework import routers
from landifys import views

r = routers.DefaultRouter()
r.register('users', views.UserViewSet, basename='user')
r.register('lists', views.ListingViewSet, basename='listing')
r.register('reports', views.ReportViewSet, basename='report')
r.register('appointments', views.AppointmentViewSet, basename='appointment')
r.register('wishlists', views.WishlistViewSet, basename='wishlist')
r.register('auth', views.AuthVerificationView, basename='auth')
r.register('properties', views.PropertyAnalysisViewSet, basename='property')
r.register('posts', views.PostViewSet, basename='post')
r.register('protests', views.ProtestViewSet, basename='protest')

urlpatterns = [
    path('', include(r.urls)),
    # path('', views.index),
    re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
]
