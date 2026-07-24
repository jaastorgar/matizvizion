from django.urls import path
from .password_views import PasswordResetConfirmView, PasswordResetRequestView

from .views import GuestView, MeView, MiPerfilView, RegistroClienteView

urlpatterns = [
    path('register/', RegistroClienteView.as_view(), name='registro_cliente'),
    path('profile/', MiPerfilView.as_view(), name='mi_perfil'),
    path('me/', MeView.as_view(), name='me'),
    path('guest/', GuestView.as_view(), name='guest'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]