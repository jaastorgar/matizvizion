from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.permissions import IsClienteUser

from .models import Categoria, Producto, RecetaOptica
from .serializers import (
    CategoriaSerializer,
    ProductoSerializer,
    RecetaOpticaSerializer,
)


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Listado público de categorías."""
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]


class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catálogo público.
    - Solo muestra productos activos (control editorial con el campo `activo`).
    - Permite filtrar por categoría: ?categoria=<id>
    - Permite buscar por texto: ?search=<texto>
    - Permite ordenar: ?ordering=precio o ?ordering=-precio
    - Expone `en_stock` para que el frontend pinte "Agotado" sin ocultar el producto.
    """
    queryset = Producto.objects.filter(activo=True).select_related('categoria')
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'destacado']
    search_fields = ['nombre', 'descripcion', 'categoria__nombre']
    ordering_fields = ['precio', 'nombre', 'creado_en']
    ordering = ['nombre']


class RecetaOpticaViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    - CLIENTE: crea y consulta solo sus propias recetas.
    - VENDEDOR/ADMIN: consulta todas.
    """
    serializer_class = RecetaOpticaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = RecetaOptica.objects.select_related('cliente__user')
        if self.request.user.role == 'CLIENTE':
            return queryset.filter(cliente__user=self.request.user)
        return queryset

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsClienteUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # La receta siempre se asigna al perfil del cliente autenticado
        try:
            perfil = self.request.user.perfil_cliente
        except Exception:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Este usuario no tiene un perfil de cliente.')

        serializer.save(cliente=perfil)