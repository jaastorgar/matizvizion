from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CarritoViewSet,
    OrdenViewSet,
    OperacionOrdenViewSet,
    TrackOrdenView,
)

router = DefaultRouter()
router.register('carrito', CarritoViewSet, basename='carrito')
router.register('ordenes', OrdenViewSet, basename='orden')
router.register('operaciones', OperacionOrdenViewSet, basename='operacion')

urlpatterns = router.urls + [
    path('track/', TrackOrdenView.as_view(), name='track-orden'),
]