from django.urls import path
from rest_framework.routers import DefaultRouter

from .devoluciones_views import SolicitudDevolucionViewSet
from .garantias_views import GarantiasClienteView, GarantiasMarcoView
from .views import CarritoViewSet, OperacionOrdenViewSet, OrdenViewSet, TrackOrdenView

router = DefaultRouter()
router.register('carrito', CarritoViewSet, basename='carrito')
router.register('ordenes', OrdenViewSet, basename='orden')
router.register('operaciones', OperacionOrdenViewSet, basename='operacion')
router.register('devoluciones', SolicitudDevolucionViewSet, basename='devolucion')

urlpatterns = router.urls + [
    path('track/', TrackOrdenView.as_view(), name='track-orden'),
    path('garantias/', GarantiasClienteView.as_view(), name='garantias-cliente'),
    path('garantias-marco/', GarantiasMarcoView.as_view(), name='garantias-marco'),
]