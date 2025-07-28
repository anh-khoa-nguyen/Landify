from django.http import HttpResponse
from rest_framework import viewsets, generics
from landifys import serializers
from landifys.models import Category

class CategoryViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.filter(active=True)
    serializer_class = serializers.CategorySerializer

def index(request):
    return HttpResponse('Hello, World!')