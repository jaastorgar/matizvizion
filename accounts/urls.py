from django.urls import path
from .password_views import PasswordResetConfirmView, PasswordResetRequestView

from .views import GuestView, MeView, MiPerfilView, RegistroClienteView

from .staff_views import StaffProfileView
urlpatterns = [
    path('register/', RegistroClienteView.as_view(), name='registro_cliente'),
    path('profile/', MiPerfilView.as_view(), name='mi_perfil'),
    path('me/', MeView.as_view(), name='me'),
    path('guest/', GuestView.as_view(), name='guest'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('staff-perfil/', StaffProfileView.as_view(), name='staff_perfil'),
]

# Alias para que /api/accounts/mi-perfil/ y /mi_perfil/ apunten al mismo perfil
from .views import MiPerfilView as _MiPerfilView
urlpatterns += [
    path('mi-perfil/', _MiPerfilView.as_view(), name='mi_perfil_h'),
    path('mi_perfil/', _MiPerfilView.as_view(), name='mi_perfil_u'),
]

from .views import ConsentimientosView as _ConsentView
urlpatterns += [path('consentimientos/', _ConsentView.as_view(), name='consentimientos')]
