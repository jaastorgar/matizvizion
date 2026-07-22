from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CustomUser, PerfilCliente
from .permissions import IsClienteUser
from .serializers import RegistroClienteSerializer, PerfilClienteSerializer

class RegistroClienteView(generics.CreateAPIView):
    serializer_class = RegistroClienteSerializer
    permission_classes = [AllowAny]

class MiPerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = PerfilClienteSerializer
    permission_classes = [IsAuthenticated, IsClienteUser]
    def get_object(self):
        try:
            return self.request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            raise NotFound('Este usuario no tiene perfil de cliente.')

class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        u = request.user
        return Response({'id': u.id, 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name, 'role': u.role})