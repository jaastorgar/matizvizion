from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Endpoints JWT Auth (Login nativo de SimpleJWT)
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Endpoints de Registro y Perfil
    path('api/accounts/', include('accounts.urls')),
    
    # API Módulos Base, E-Commerce, Pagos y Agendamiento Clínico
    path('api/core/', include('core.urls')),
    path('api/store/', include('store.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/appointments/', include('appointments.urls')),
]