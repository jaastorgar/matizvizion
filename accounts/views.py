from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import PerfilCliente
from .permissions import IsClienteUser
from .serializers import RegistroClienteSerializer, PerfilClienteSerializer


class RegistroClienteView(generics.CreateAPIView):
    """
    Endpoint público para crear un nuevo usuario con rol CLIENTE.
    """
    serializer_class = RegistroClienteSerializer
    permission_classes = [AllowAny]


class MiPerfilView(generics.RetrieveUpdateAPIView):
    """
    Permite a un cliente autenticado ver y editar sus datos de perfil.
    """
    serializer_class = PerfilClienteSerializer
    permission_classes = [IsAuthenticated, IsClienteUser]

    def get_object(self):
        try:
            return self.request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            raise NotFound('Este usuario no tiene un perfil de cliente asociado.')