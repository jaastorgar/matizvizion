from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('carrito/', views.carrito, name='carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('pago/retorno/', views.pago_retorno, name='pago_retorno'),
    path('citas/', views.reserva, name='reserva'),
    path('panel/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
]