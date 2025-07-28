from django.urls import path, include, re_path
from rest_framework import routers
from landifys import views

r = routers.DefaultRouter()
r.register('categories', views.CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(r.urls)),
    # path('', views.index),

    re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
]
