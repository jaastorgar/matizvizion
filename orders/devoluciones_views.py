from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsVendedorUser
from .models import ItemOrden, Orden, ResolucionDevolucion, SolicitudDevolucion

RESOLUCIONES_VALIDAS = [c for c, _ in ResolucionDevolucion.choices]


class SolicitudDevolucionSerializer(serializers.ModelSerializer):
    orden_codigo = serializers.ReadOnlyField(source='orden.codigo')
    orden_estado = serializers.ReadOnlyField(source='orden.estado')
    cliente_email = serializers.ReadOnlyField(source='cliente.email')
    items_detalle = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudDevolucion
        fields = ['id', 'orden', 'orden_codigo', 'orden_estado', 'cliente', 'cliente_email',
                  'motivo', 'estado', 'resolucion', 'garantia_aplicada', 'items_detalle',
                  'motivo_rechazo', 'reembolso_procesado', 'creado_en', 'resuelto_en']
        read_only_fields = fields

    def get_items_detalle(self, obj):
        out = []
        for it in obj.items.select_related('producto').all():
            out.append({
                'item_id': it.id,
                'sku': getattr(it.producto, 'sku', '') or '',
                'nombre': it.producto.nombre,
                'cantidad': it.cantidad,
                'precio': float(it.precio_unitario or 0),
            })
        return out


class SolicitudDevolucionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SolicitudDevolucionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SolicitudDevolucion.objects.select_related('orden', 'cliente').prefetch_related('items__producto')
        if self.request.user.role == 'CLIENTE':
            return qs.filter(cliente=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        orden_id = request.data.get('orden')
        motivo = (request.data.get('motivo') or '').strip()
        skus = request.data.get('items') or []
        if isinstance(skus, str):
            skus = [skus]
        skus = [str(s).strip().upper() for s in skus if str(s).strip()]
        if not orden_id or not motivo:
            return Response({'error': 'Debes indicar la orden y el motivo.'}, status=status.HTTP_400_BAD_REQUEST)
        if not skus:
            return Response({'error': 'Selecciona al menos un producto a devolver.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            orden = Orden.objects.get(pk=orden_id, cliente=request.user)
        except Orden.DoesNotExist:
            return Response({'error': 'Orden no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if orden.estado not in (Orden.Estado.ENTREGADA, Orden.Estado.ENVIADA):
            return Response({'error': 'Solo puedes solicitar devolucion de un pedido entregado o enviado.'},
                            status=status.HTTP_400_BAD_REQUEST)
        # Resuelve los ItemOrden de la orden por SKU (un SKU por linea dentro de la orden).
        item_qs = orden.items.filter(producto__sku__in=skus)
        encontrados = set(item_qs.values_list('producto__sku', flat=True))
        faltan = [s for s in skus if s not in encontrados]
        if faltan:
            return Response({'error': 'Uno o mas productos no corresponden a este pedido.'},
                            status=status.HTTP_400_BAD_REQUEST)
        # No permitir devolver de nuevo lineas ya en proceso o ya aprobadas.
        en_curso = SolicitudDevolucion.objects.filter(
            orden=orden, estado__in=['PENDIENTE', 'APROBADA'], items__producto__sku__in=skus
        ).distinct()
        if en_curso.exists():
            return Response({'error': 'Algun producto seleccionado ya tiene una devolucion en curso o aprobada.'},
                            status=status.HTTP_400_BAD_REQUEST)
        sol = SolicitudDevolucion.objects.create(orden=orden, cliente=request.user, motivo=motivo)
        sol.items.set(item_qs)
        return Response(self.get_serializer(sol).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='aprobar', permission_classes=[IsVendedorUser])
    def aprobar(self, request, pk=None):
        sol = self.get_object()
        if sol.estado != 'PENDIENTE':
            return Response({'error': 'Esta solicitud ya fue resuelta.'}, status=status.HTTP_400_BAD_REQUEST)
        resolucion = (request.data.get('resolucion') or 'devolucion').strip().lower()
        if resolucion not in RESOLUCIONES_VALIDAS:
            return Response({'error': 'Resolucion invalida.'}, status=status.HTTP_400_BAD_REQUEST)
        garantia = (request.data.get('garantia_aplicada') or '').strip() or None

        with transaction.atomic():
            orden = Orden.objects.select_for_update().get(pk=sol.orden_id)
            if resolucion == ResolucionDevolucion.DEVOLUCION:
                sol.revertir_stock_items()  # repone SOLO los productos de la solicitud
                orden_ids = set(orden.items.values_list('id', flat=True))
                sol_ids = set(sol.items.values_list('id', flat=True))
                # La orden pasa a DEVUELTA solo si se devuelven TODAS sus lineas.
                if sol_ids and sol_ids == orden_ids and orden.puede_cambiar_a(Orden.Estado.DEVUELTA):
                    orden.cambiar_estado(Orden.Estado.DEVUELTA, usuario=request.user)
            sol.resolucion = resolucion
            sol.garantia_aplicada = garantia
            sol.estado = 'APROBADA'
            sol.resuelto_en = timezone.now()
            sol.resuelto_por = request.user
            sol.save(update_fields=['resolucion', 'garantia_aplicada', 'estado', 'resuelto_en', 'resuelto_por'])
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