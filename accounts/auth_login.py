from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginSerializer(TokenObtainPairSerializer):
    """Login JWT con mensajes seguros contra enumeracion de usuarios."""

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except exceptions.AuthenticationFailed:
            User = get_user_model()
            ident = str(attrs.get(self.username_field, '') or '').strip().lower()
            user = None
            if ident:
                try:
                    user = User.objects.filter(email__iexact=ident).first()
                except Exception:
                    user = None
            if user and not getattr(user, 'is_active', True):
                raise exceptions.AuthenticationFailed('Tu cuenta está desactivada. Contacta a soporte.')
            raise exceptions.AuthenticationFailed('Correo electrónico o contraseña incorrectos. Intenta nuevamente.')


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [AnonRateThrottle]

