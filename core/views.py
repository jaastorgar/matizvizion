from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Sucursal
from .serializers import SucursalSerializer


class SucursalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permite listar y recuperar sucursales de forma pública.
    Solo muestra sucursales activas.
    """
    queryset = Sucursal.objects.filter(activa=True)
    serializer_class = SucursalSerializer
    permission_classes = [AllowAny]