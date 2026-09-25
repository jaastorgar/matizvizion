from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model


class LoginSerializer(TokenObtainPairSerializer):
    """Login JWT con mensajes exactos (en vez del generico confuso)."""

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except exceptions.AuthenticationFailed:
            User = get_user_model()
            ident = str(attrs.get(self.username_field, '') or '')
            user = None
            try:
                user = User.objects.filter(**{self.username_field: ident}).first()
            except Exception:
                user = None
            if user is None:
                try:
                    user = User.objects.filter(email__iexact=ident).first()
                except Exception:
                    user = None
            if user is None:
                raise exceptions.AuthenticationFailed('No existe una cuenta con este correo electronico.')
            if not getattr(user, 'is_active', True):
                raise exceptions.AuthenticationFailed('Tu cuenta esta desactivada. Contacta a soporte.')
            raise exceptions.AuthenticationFailed('Contrasena incorrecta. Intenta nuevamente.')


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
