from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, PerfilCliente
from .permissions import IsClienteUser
from .serializers import PerfilClienteSerializer, RegistroClienteSerializer


class RegistroClienteView(generics.CreateAPIView):
    serializer_class = RegistroClienteSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    """Datos basicos del usuario autenticado (incluye is_guest)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'is_guest': getattr(u, 'is_guest', False),
        })


class MiPerfilView(APIView):
    """
    Perfil de cliente con UPSERT: si el usuario (p.ej. un invitado) aun no
    tiene PerfilCliente, el GET devuelve campos vacios y el PUT/PATCH lo crea.
    """
    permission_classes = [IsAuthenticated, IsClienteUser]

    def get(self, request):
        try:
            perfil = request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            return Response({'rut': '', 'telefono': '', 'direccion': ''})
        return Response(PerfilClienteSerializer(perfil).data)

    def put(self, request):
        return self._upsert(request, partial=False)

    def patch(self, request):
        return self._upsert(request, partial=True)

    def _upsert(self, request, partial):
        try:
            perfil = request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            perfil = None
        ser = PerfilClienteSerializer(perfil, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        if perfil is None:
            try:
                perfil = ser.save(user=request.user)
            except IntegrityError:
                return Response(
                    {'rut': 'Ese RUT ya esta registrado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            ser.save()
        return Response(PerfilClienteSerializer(perfil).data)


class GuestView(APIView):
    """
    Compra como invitado: crea (o reusa) un usuario sin contraseña a partir
    del email y devuelve un JWT. No crea PerfilCliente (se pedira despues).
    - email invalido            -> 400
    - email ya es cuenta real   -> 409 (debe iniciar sesion)
    - email ya es invitado      -> reusa y emite token (no duplica)
    - email nuevo               -> crea invitado y emite token
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'email': 'Debes indicar un correo electrónico.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response(
                {'email': 'El correo electrónico no es válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = CustomUser.objects.filter(email=email).first()
        if existing:
            if existing.has_usable_password():
                return Response(
                    {'email': 'Ese correo ya tiene una cuenta. Inicia sesión.'},
                    status=status.HTTP_409_CONFLICT,
                )
            user = existing
            created = False
        else:
            user = CustomUser.objects.create_guest(email=email)
            created = True

        token = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(token.access_token),
                'refresh': str(token),
                'is_guest': user.is_guest,
                'role': user.role,
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )