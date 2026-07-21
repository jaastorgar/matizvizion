from django.urls import path
from .views import RegistroClienteView, MiPerfilView

urlpatterns = [
    path('register/', RegistroClienteView.as_view(), name='registro_cliente'),
    path('profile/', MiPerfilView.as_view(), name='mi_perfil'),
]