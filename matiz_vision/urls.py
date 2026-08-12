from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from core.kpis_views import KpisView

from core.admin_api import admin_router, StatsView
urlpatterns = [
    path('api/admin/', include(admin_router.urls)),
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
    # Inteligencia de negocio (solo ADMIN)
    path('api/admin/kpis/', KpisView.as_view(), name='admin-kpis'),
    # Páginas HTML (capa de presentación)
    path('api/admin/stats/', StatsView.as_view()),
    path('', include('web.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)