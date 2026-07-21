from rest_framework.routers import DefaultRouter

from .views import SucursalViewSet


app_name = 'core'


router = DefaultRouter()
router.register(
    'sucursales',
    SucursalViewSet,
    basename='sucursal'
)


urlpatterns = router.urls