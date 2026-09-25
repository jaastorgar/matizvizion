from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('', views.RecetaViewSet, basename='receta')

urlpatterns = [
    path('', include(router.urls)),
]
