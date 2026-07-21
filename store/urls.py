from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, ProductoViewSet, RecetaOpticaViewSet


app_name = 'store'


router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('productos', ProductoViewSet, basename='producto')
router.register('recetas', RecetaOpticaViewSet, basename='receta')


urlpatterns = router.urls