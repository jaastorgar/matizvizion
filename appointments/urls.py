from rest_framework.routers import DefaultRouter

from .views import BloqueHorarioViewSet, CitaMedicaViewSet, TecnologoViewSet


app_name = 'appointments'


router = DefaultRouter()
router.register('tecnologos', TecnologoViewSet, basename='tecnologo')
router.register('bloques', BloqueHorarioViewSet, basename='bloquehorario')
router.register('citas', CitaMedicaViewSet, basename='citamedica')


urlpatterns = router.urls