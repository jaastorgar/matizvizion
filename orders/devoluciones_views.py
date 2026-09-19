from django.db import transaction
from django.db.models import Q
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
                'cantidad_devuelta': obj.cantidad_de(it),
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
        raw_items = request.data.get('items') or []
        if isinstance(raw_items, str):
            raw_items = [raw_items]
        pedido = []
        for it in raw_items:
            if isinstance(it, dict):
                sku = str(it.get('sku') or '').strip().upper()
                qty = it.get('cantidad')
                qty = int(qty) if qty not in (None, '') else None
            else:
                sku = str(it).strip().upper()
                qty = None
            if sku:
                pedido.append((sku, qty))
        if not orden_id or not motivo:
            return Response({'error': 'Debes indicar la orden y el motivo.'}, status=status.HTTP_400_BAD_REQUEST)
        if not pedido:
            return Response({'error': 'Selecciona al menos un producto a devolver.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            orden = Orden.objects.get(pk=orden_id, cliente=request.user)
        except Orden.DoesNotExist:
            return Response({'error': 'Orden no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if orden.estado not in (Orden.Estado.ENTREGADA, Orden.Estado.ENVIADA):
            return Response({'error': 'Solo puedes solicitar devolucion de un pedido entregado o enviado.'},
                            status=status.HTTP_400_BAD_REQUEST)
        skus = [s for s, _ in pedido]
        item_qs = orden.items.filter(producto__sku__in=skus)
        by_sku = {it.producto.sku: it for it in item_qs}
        faltan = [s for s in skus if s not in by_sku]
        if faltan:
            return Response({'error': 'Uno o mas productos no corresponden a este pedido.'},
                            status=status.HTTP_400_BAD_REQUEST)
        prev = SolicitudDevolucion.objects.filter(orden=orden).filter(
            Q(estado='PENDIENTE') | Q(estado='APROBADA', resolucion='devolucion')
        ).prefetch_related('items')
        usadas = {}
        for s in prev:
            for it in s.items.all():
                usadas[it.id] = usadas.get(it.id, 0) + s.cantidad_de(it)
        cant_map = {}
        for sku, qty in pedido:
            item = by_sku[sku]
            remaining = item.cantidad - usadas.get(item.id, 0)
            if remaining <= 0:
                return Response({'error': f'{sku} ya tiene una devolucion en curso o aprobada por el total de la linea.'},
                                status=status.HTTP_400_BAD_REQUEST)
            q = qty if qty is not None else remaining
            if q <= 0 or q > remaining:
                return Response({'error': f'Cantidad invalida para {sku}: puedes devolver hasta {remaining} unidad(es).'},
                                status=status.HTTP_400_BAD_REQUEST)
            cant_map[str(item.id)] = q
        sol = SolicitudDevolucion.objects.create(
            orden=orden, cliente=request.user, motivo=motivo, cantidades=cant_map
        )
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
                sol.revertir_stock_items()
            sol.resolucion = resolucion
            sol.garantia_aplicada = garantia
            sol.estado = 'APROBADA'
            sol.resuelto_en = timezone.now()
            sol.resuelto_por = request.user
            sol.save(update_fields=['resolucion', 'garantia_aplicada', 'estado', 'resuelto_en', 'resuelto_por'])
            if resolucion == ResolucionDevolucion.DEVOLUCION:
                totales = {}
                sols = SolicitudDevolucion.objects.filter(
                    orden=orden, estado='APROBADA', resolucion='devolucion'
                ).prefetch_related('items')
                for s in sols:
                    for it in s.items.all():
                        totales[it.id] = totales.get(it.id, 0) + s.cantidad_de(it)
                completo = all(totales.get(it.id, 0) >= it.cantidad for it in orden.items.all())
                if completo and orden.puede_cambiar_a(Orden.Estado.DEVUELTA):
                    orden.cambiar_estado(Orden.Estado.DEVUELTA, usuario=request.user)
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
