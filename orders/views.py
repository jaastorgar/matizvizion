from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsVendedorUser
from store.models import Producto

from .models import (
    Carrito,
    HistorialEstado,
    ItemCarrito,
    ItemOrden,
    Orden,
)
from .serializers import ItemCarritoSerializer, OrdenSerializer


class CarritoViewSet(viewsets.ModelViewSet):
    """
    Permite al cliente autenticado gestionar los items de su carrito.
    """
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
                raise ValidationError(
                    {
                        'cantidad': f'Stock insuficiente para {producto.nombre}.'
                    }
                )

            item = serializer.save(
                carrito=carrito,
                producto=producto
            )

        return Response(
            self.get_serializer(item).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            producto = serializer.validated_data.get(
                'producto',
                instance.producto
            )
            producto = Producto.objects.select_for_update().get(pk=producto.pk)

            cantidad = serializer.validated_data.get(
                'cantidad',
                instance.cantidad
            )

            if producto.stock < cantidad:
                raise ValidationError(
                    {
                        'cantidad': f'Stock insuficiente para {producto.nombre}.'
                    }
                )

            item = serializer.save(producto=producto)

        return Response(self.get_serializer(item).data)


class OrdenViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Permite al cliente crear órdenes desde su carrito y consultar sus propias órdenes.
    """
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Orden.objects.filter(
            cliente=self.request.user
        ).select_related('cliente').prefetch_related(
            'items__producto',
            'historial'
        ).order_by('-creado_en')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        carrito = Carrito.objects.filter(
            cliente=request.user
        ).prefetch_related('items__producto').first()

        if not carrito or not carrito.items.exists():
            raise ValidationError(
                {
                    'carrito': 'El carrito está vacío.'
                }
            )

        items = list(carrito.items.select_related('producto').all())

        cantidades_por_producto = defaultdict(int)

        for item in items:
            cantidades_por_producto[item.producto_id] += item.cantidad

        productos = {
            producto.pk: producto
            for producto in Producto.objects.select_for_update().filter(
                pk__in=cantidades_por_producto.keys()
            )
        }

        # Validar existencia y stock
        for producto_id, cantidad_total in cantidades_por_producto.items():
            producto = productos.get(producto_id)

            if not producto:
                raise ValidationError(
                    {
                        'producto': 'Uno de los productos del carrito ya no existe.'
                    }
                )

            if cantidad_total <= 0:
                raise ValidationError(
                    {
                        'cantidad': 'La cantidad debe ser mayor que cero.'
                    }
                )

            if producto.stock < cantidad_total:
                raise ValidationError(
                    {
                        'stock': f'Stock insuficiente para {producto.nombre}.'
                    }
                )

        total_orden = sum(
            (
                productos[producto_id].precio * cantidad_total
                for producto_id, cantidad_total in cantidades_por_producto.items()
            ),
            Decimal('0')
        )

        orden = Orden.objects.create(
            cliente=request.user,
            total=total_orden,
            estado=Orden.Estado.PENDIENTE
        )

        HistorialEstado.objects.create(
            orden=orden,
            estado_anterior='',
            estado_nuevo=Orden.Estado.PENDIENTE,
            usuario=request.user
        )

        # Crear items de orden y descontar stock
        for producto_id, cantidad_total in cantidades_por_producto.items():
            producto = productos[producto_id]

            ItemOrden.objects.create(
                orden=orden,
                producto=producto,
                precio_unitario=producto.precio,
                cantidad=cantidad_total
            )

            producto.stock = F('stock') - cantidad_total
            producto.save(update_fields=['stock'])

        # Vaciar carrito
        carrito.items.all().delete()

        serializer = self.get_serializer(orden)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


class OperacionOrdenViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Panel para vendedores.
    Permite ver órdenes operativas y actualizar su estado de entrega.
    """
    serializer_class = OrdenSerializer
    permission_classes = [IsVendedorUser]

    def get_queryset(self):
        return Orden.objects.filter(
            estado__in=[
                Orden.Estado.PAGADA,
                Orden.Estado.EN_PREPARACION,
                Orden.Estado.ENVIADA,
            ]
        ).select_related('cliente').prefetch_related(
            'items__producto',
            'historial'
        ).order_by('creado_en')

    @action(detail=True, methods=['patch'], url_path='actualizar-entrega')
    def actualizar_entrega(self, request, pk=None):
        nuevo_estado = request.data.get('estado')

        if not nuevo_estado:
            return Response(
                {
                    'error': 'Debes enviar el campo "estado".'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        orden = self.get_object()

        try:
            with transaction.atomic():
                orden = Orden.objects.select_for_update().get(pk=orden.pk)
                orden.cambiar_estado(
                    nuevo_estado=nuevo_estado,
                    usuario=request.user
                )
        except ValueError as error:
            return Response(
                {
                    'error': str(error)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(self.get_serializer(orden).data)