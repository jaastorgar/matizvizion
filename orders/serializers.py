from rest_framework import serializers

from .models import (
    HistorialEstado,
    ItemCarrito,
    ItemOrden,
    Orden,
)


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source='producto.nombre',
        read_only=True
    )
    precio_unitario = serializers.DecimalField(
        source='producto.precio',
        read_only=True,
        max_digits=10,
        decimal_places=2
    )
    subtotal = serializers.DecimalField(
        read_only=True,
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        model = ItemCarrito
        fields = [
            'id',
            'producto',
            'producto_nombre',
            'precio_unitario',
            'cantidad',
            'subtotal',
        ]
        read_only_fields = ['id']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor que cero.')
        return value

    def validate(self, data):
        producto = data.get(
            'producto',
            getattr(self.instance, 'producto', None)
        )
        cantidad = data.get(
            'cantidad',
            getattr(self.instance, 'cantidad', 1)
        )

        if producto and cantidad > producto.stock:
            raise serializers.ValidationError(
                {
                    'cantidad': f'Stock insuficiente para {producto.nombre}.'
                }
            )

        return data


class ItemOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source='producto.nombre',
        read_only=True
    )
    subtotal = serializers.DecimalField(
        read_only=True,
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        model = ItemOrden
        fields = [
            'id',
            'producto',
            'producto_nombre',
            'precio_unitario',
            'cantidad',
            'subtotal',
        ]
        read_only_fields = [
            'id',
            'producto',
            'precio_unitario',
            'cantidad',
        ]


class HistorialEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEstado
        fields = [
            'id',
            'estado_anterior',
            'estado_nuevo',
            'cambiado_en',
        ]
        read_only_fields = [
            'id',
            'estado_anterior',
            'estado_nuevo',
            'cambiado_en',
        ]


class OrdenSerializer(serializers.ModelSerializer):
    cliente_email = serializers.EmailField(
        source='cliente.email',
        read_only=True
    )
    items = ItemOrdenSerializer(
        many=True,
        read_only=True
    )
    historial = HistorialEstadoSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Orden
        fields = [
            'id',
            'cliente',
            'cliente_email',
            'total',
            'estado',
            'creado_en',
            'actualizado_en',
            'items',
            'historial',
        ]
        read_only_fields = [
            'cliente',
            'total',
            'estado',
            'creado_en',
            'actualizado_en',
        ]