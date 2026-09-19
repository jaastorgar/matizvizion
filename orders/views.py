from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsVendedorUser
from store.models import Producto

from .models import Carrito, HistorialEstado, ItemCarrito, ItemOrden, Orden
from .serializers import (
    ItemCarritoSerializer,
    OrdenSerializer,
    SeguimientoPublicoSerializer,
)

# Para el cliente, una "compra" es una orden que ya paso del intento/abandono
ESTADOS_COMPRA_CLIENTE = [
    Orden.Estado.PAGADA,
    Orden.Estado.EN_PREPARACION,
    Orden.Estado.LISTO_PARA_RETIRO,
    Orden.Estado.ENVIADA,
    Orden.Estado.ENTREGADA,
]


class CarritoViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_carrito(self):
        carrito, _ = Carrito.objects.get_or_create(cliente=self.request.user)
        return carrito

    def get_queryset(self):
        return ItemCarrito.objects.filter(
            carrito=self.get_carrito()
        ).select_related('producto')

    def create(self, request, *args, **kwargs):
        carrito = self.get_carrito()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.validated_data['producto']
        cantidad = serializer.validated_data.get('cantidad', 1)
        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(pk=producto.pk)
            if producto.stock < cantidad:
                raise ValidationError({'cantidad': f'Stock insuficiente para {producto.nombre}.'})
            item = serializer.save(carrito=carrito, producto=producto)
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            producto = serializer.validated_data.get('producto', instance.producto)
            producto = Producto.objects.select_for_update().get(pk=producto.pk)
            cantidad = serializer.validated_data.get('cantidad', instance.cantidad)
            if producto.stock < cantidad:
                raise ValidationError({'cantidad': f'Stock insuficiente para {producto.nombre}.'})
            item = serializer.save(producto=producto)
        return Response(self.get_serializer(item).data)


class OrdenViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Orden.objects.filter(cliente=self.request.user).select_related(
            'cliente'
        ).prefetch_related('items__producto', 'historial').order_by('-creado_en')
        # El cliente solo ve sus COMPRAS reales (no reservas pendientes ni intentos fallidos)
        if self.request.user.role == 'CLIENTE':
            qs = qs.filter(estado__in=ESTADOS_COMPRA_CLIENTE)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        carrito = Carrito.objects.filter(
            cliente=request.user
        ).prefetch_related('items__producto').first()
        if not carrito or not carrito.items.exists():
            raise ValidationError({'carrito': 'El carrito esta vacio.'})
        items = list(carrito.items.select_related('producto').all())
        cantidades = defaultdict(int)
        for item in items:
            cantidades[item.producto_id] += item.cantidad
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(pk__in=cantidades.keys())
        }
        for pid, cant in cantidades.items():
            prod = productos.get(pid)
            if not prod:
                raise ValidationError({'producto': 'Uno de los productos del carrito ya no existe.'})
            if cant <= 0:
                raise ValidationError({'cantidad': 'La cantidad debe ser mayor que cero.'})
            if prod.stock < cant:
                raise ValidationError({'stock': f'Stock insuficiente para {prod.nombre}.'})
        total = sum(
            (productos[pid].precio * c for pid, c in cantidades.items()),
            Decimal('0'),
        )
        modo_pago = (request.data.get('modo_pago') or 'COMPLETO').upper()
        if modo_pago not in ('COMPLETO', 'ABONO'):
            raise ValidationError({'modo_pago': 'Modalidad de pago invalida.'})
        monto_abonado = Decimal('0')
        if modo_pago == 'ABONO':
            monto_abonado = (total / 2).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        orden = Orden.objects.create(
            cliente=request.user, total=total, estado=Orden.Estado.PENDIENTE,
            modo_pago=modo_pago, monto_abonado=monto_abonado,
        )
        HistorialEstado.objects.create(
            orden=orden, estado_anterior='', estado_nuevo=Orden.Estado.PENDIENTE, usuario=request.user
        )
        # Cada linea de la orden conserva la configuracion optica elegida en el catalogo
        for item in items:
            prod = productos[item.producto_id]
            ItemOrden.objects.create(
                orden=orden, producto=prod, precio_unitario=prod.precio,
                cantidad=item.cantidad, tipo_lente=item.tipo_lente, uso_lente=item.uso_lente,
            )
            prod.stock = F('stock') - item.cantidad
            prod.save(update_fields=['stock'])
        carrito.items.all().delete()
        return Response(self.get_serializer(orden).data, status=status.HTTP_201_CREATED)

class OperacionOrdenViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrdenSerializer
    permission_classes = [IsVendedorUser]

    def get_queryset(self):
        # Incluye LISTO_PARA_RETIRO para el flujo de retiro en tienda
        return Orden.objects.filter(
            estado__in=[
                Orden.Estado.PAGADA,
                Orden.Estado.EN_PREPARACION,
                Orden.Estado.LISTO_PARA_RETIRO,
                Orden.Estado.ENVIADA,
            ]
        ).select_related('cliente').prefetch_related(
            'items__producto', 'historial'
        ).order_by('creado_en')

    @action(detail=True, methods=['patch'], url_path='actualizar-entrega')
    def actualizar_entrega(self, request, pk=None):
        nuevo_estado = request.data.get('estado')
        if not nuevo_estado:
            return Response(
                {'error': 'Debes enviar el campo "estado".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        orden = self.get_object()
        try:
            with transaction.atomic():
                orden = Orden.objects.select_for_update().get(pk=orden.pk)
                # Si se cancela una orden que ya habia descontado stock,
                # el inventario vuelve al estante (retiro en tienda: el producto no salio del local).
                if nuevo_estado == 'CANCELADA' and orden.estado not in ('CANCELADA', 'FALLIDA'):
                    orden.revertir_stock()
            if nuevo_estado == Orden.Estado.ENTREGADA and getattr(orden, 'modo_pago', 'COMPLETO') == 'ABONO' and not orden.saldo_cancelado:
                return Response({'error': 'Registra el pago del saldo en tienda antes de marcar entregada.'}, status=status.HTTP_400_BAD_REQUEST)
            orden.cambiar_estado(nuevo_estado=nuevo_estado, usuario=request.user)
        except ValueError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(orden).data)


    @action(detail=True, methods=['post'], url_path='confirmar-saldo')
    def confirmar_saldo(self, request, pk=None):
        orden = self.get_object()
        if getattr(orden, 'modo_pago', 'COMPLETO') != 'ABONO':
            return Response({'error': 'La orden es de pago completo; no tiene saldo.'}, status=status.HTTP_400_BAD_REQUEST)
        if orden.saldo_cancelado:
            return Response({'message': 'El saldo ya estaba cancelado.', 'saldo_cancelado': True}, status=status.HTTP_200_OK)
        orden.saldo_cancelado = True
        orden.saldo_cancelado_en = timezone.now()
        orden.save(update_fields=['saldo_cancelado', 'saldo_cancelado_en', 'actualizado_en'])
        return Response(self.get_serializer(orden).data)


class TrackOrdenView(APIView):
    """
    Buscador PUBLICO de seguimiento por codigo de pedido.
    Seguro por diseno: el codigo no es secuencial (no se puede enumerar) y
    NUNCA se exponen email, RUT ni direccion (SeguimientoPublicoSerializer).
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        codigo = (request.query_params.get('codigo') or '').strip().upper()
        if not codigo:
            return Response(
                {'error': 'Debes indicar el codigo de pedido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            orden = Orden.objects.prefetch_related('items__producto').get(codigo__iexact=codigo)
        except Orden.DoesNotExist:
            # Mensaje generico: no revelamos si el codigo "casi" existe
            return Response(
                {'error': 'No encontramos un pedido con ese codigo.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SeguimientoPublicoSerializer(orden).data)


