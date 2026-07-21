from rest_framework.routers import DefaultRouter

from .views import (
    CarritoViewSet,
    OperacionOrdenViewSet,
    OrdenViewSet,
)


app_name = 'orders'


router = DefaultRouter()
router.register(
    'carrito',
    CarritoViewSet,
    basename='carrito'
)
router.register(
    'ordenes',
    OrdenViewSet,
    basename='orden'
)
router.register(
    'operaciones',
    OperacionOrdenViewSet,
    basename='operacion'
)


urlpatterns = router.urls