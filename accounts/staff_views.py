from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class StaffProfileView(APIView):
    """Datos del perfil del staff (vendedor/admin), autenticado por JWT."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        pv = getattr(u, 'perfil_vendedor', None)
        return Response({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'is_superuser': u.is_superuser,
            'date_joined': u.date_joined,
            'sucursal': (pv.sucursal.nombre if (pv and pv.sucursal) else None),
            'codigo_vendedor': (pv.codigo_vendedor if pv else None),
        })