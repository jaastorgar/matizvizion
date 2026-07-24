from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from accounts.permissions import IsVendedorUser
from .models import Orden, SolicitudDevolucion


class SolicitudDevolucionSerializer(serializers.ModelSerializer):
    orden_codigo = serializers.ReadOnlyField(source='orden.codigo')
    orden_estado = serializers.ReadOnlyField(source='orden.estado')
    cliente_email = serializers.ReadOnlyField(source='cliente.email')

    class Meta:
        model = SolicitudDevolucion
        fields = ['id', 'orden', 'orden_codigo', 'orden_estado', 'cliente', 'cliente_email',
                  'motivo', 'estado', 'motivo_rechazo', 'reembolso_procesado', 'creado_en', 'resuelto_en']
        read_only_fields = ['id', 'cliente', 'cliente_email', 'orden_codigo', 'orden_estado',
                            'estado', 'motivo_rechazo', 'reembolso_procesado', 'creado_en', 'resuelto_en']


class SolicitudDevolucionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SolicitudDevolucionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SolicitudDevolucion.objects.select_related('orden', 'cliente')
        if self.request.user.role == 'CLIENTE':
            return qs.filter(cliente=self.request.user)
        return qs  # vendedor/admin ve todas

    def create(self, request, *args, **kwargs):
        orden_id = request.data.get('orden')
        motivo = (request.data.get('motivo') or '').strip()
        if not orden_id or not motivo:
            return Response({'error': 'Debes indicar la orden y el motivo.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            orden = Orden.objects.get(pk=orden_id, cliente=request.user)
        except Orden.DoesNotExist:
            return Response({'error': 'Orden no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if orden.estado not in (Orden.Estado.ENTREGADA, Orden.Estado.ENVIADA):
            return Response({'error': 'Solo puedes solicitar devolucion de un pedido entregado o enviado.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if SolicitudDevolucion.objects.filter(orden=orden, estado='PENDIENTE').exists():
            return Response({'error': 'Ya tienes una solicitud pendiente para este pedido.'},
                            status=status.HTTP_400_BAD_REQUEST)
        sol = SolicitudDevolucion.objects.create(orden=orden, cliente=request.user, motivo=motivo)
        return Response(self.get_serializer(sol).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='aprobar', permission_classes=[IsVendedorUser])
    def aprobar(self, request, pk=None):
        sol = self.get_object()
        if sol.estado != 'PENDIENTE':
            return Response({'error': 'Esta solicitud ya fue resuelta.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            orden = Orden.objects.select_for_update().get(pk=sol.orden_id)
            if not orden.puede_cambiar_a(Orden.Estado.DEVUELTA):
                return Response({'error': f'La orden no puede devolverse desde {orden.estado}.'},
                                status=status.HTTP_400_BAD_REQUEST)
            orden.revertir_stock()              # el producto vuelve al inventario
            orden.cambiar_estado(Orden.Estado.DEVUELTA, usuario=request.user)  # -> signal manda mail
            sol.estado = 'APROBADA'
            sol.resuelto_en = timezone.now()
            sol.resuelto_por = request.user
            sol.save(update_fields=['estado', 'resuelto_en', 'resuelto_por'])
        return Response(self.get_serializer(sol).data)

    @action(detail=True, methods=['post'], url_path='rechazar', permission_classes=[IsVendedorUser])
    def rechazar(self, request, pk=None):
        sol = self.get_object()
        if sol.estado != 'PENDIENTE':
            return Response({'error': 'Esta solicitud ya fue resuelta.'}, status=status.HTTP_400_BAD_REQUEST)
        motivo = (request.data.get('motivo_rechazo') or '').strip()
        sol.estado = 'RECHAZADA'
        sol.motivo_rechazo = motivo
        sol.resuelto_en = timezone.now()
        sol.resuelto_por = request.user
        sol.save(update_fields=['estado', 'motivo_rechazo', 'resuelto_en', 'resuelto_por'])
        return Response(self.get_serializer(sol).data)