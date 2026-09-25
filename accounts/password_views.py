from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.notifications import notify_password_reset
from .models import CustomUser
from .tokens import password_reset_token


class PasswordResetRequestView(APIView):
    """Pide el envio del mail de recuperacion. No revela si el email existe."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        user = CustomUser.objects.filter(email__iexact=email).first() if email else None
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token.make_token(user)
            base = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            reset_url = f"{base}/reset-password/?uid={uid}&token={token}"
            notify_password_reset(user, reset_url)
        return Response({'ok': True})


class PasswordResetConfirmView(APIView):
    """Valida uid+token y fija la nueva contrasena. Gradua invitados."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_pw = request.data.get('new_password') or ''
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Enlace invalido o expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        ok = password_reset_token.check_token(user, token)
        if not ok:
            return Response({'error': 'Enlace invalido o expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_pw, user)
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_pw)
        if getattr(user, 'is_guest', False):
            user.is_guest = False
        user.save()
        return Response({'ok': True})