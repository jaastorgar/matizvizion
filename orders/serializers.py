from rest_framework import serializers
from .models import Carrito, ItemCarrito, Orden, ItemOrden, HistorialEstado


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.sku')
    precio_unitario = serializers.ReadOnlyField(source='producto.precio')
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'producto_nombre', 'producto_sku', 'precio_unitario', 'cantidad', 'subtotal']


class ItemOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.sku')
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = ItemOrden
        fields = ['id', 'producto', 'producto_nombre', 'producto_sku', 'precio_unitario', 'cantidad', 'subtotal']


class HistorialEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEstado
        fields = ['id', 'estado_anterior', 'estado_nuevo', 'cambiado_en']


class OrdenSerializer(serializers.ModelSerializer):
    cliente_email = serializers.ReadOnlyField(source='cliente.email')
    cliente_rut = serializers.SerializerMethodField()
    items = ItemOrdenSerializer(many=True, read_only=True)
    historial = HistorialEstadoSerializer(many=True, read_only=True)

    class Meta:
        model = Orden
        fields = [
            'id', 'codigo', 'cliente', 'cliente_email', 'cliente_rut',
            'total', 'estado', 'creado_en', 'items', 'historial',
        ]
        read_only_fields = ['id', 'codigo', 'cliente', 'cliente_email', 'cliente_rut', 'total', 'estado', 'creado_en', 'items', 'historial']

    def get_cliente_rut(self, obj):
        try:
            return obj.cliente.perfil_cliente.rut
        except Exception:
            return None


class SeguimientoPublicoItemSerializer(serializers.ModelSerializer):
    """Datos NO sensibles de un producto, para el buscador publico."""
    nombre = serializers.ReadOnlyField(source='producto.nombre')
    sku = serializers.ReadOnlyField(source='producto.sku')

    class Meta:
        model = ItemOrden
        fields = ['nombre', 'sku', 'cantidad']


class SeguimientoPublicoSerializer(serializers.ModelSerializer):
    """Vista publica y limitada del pedido: SIN email, RUT ni direccion."""
    items = SeguimientoPublicoItemSerializer(many=True, read_only=True)

    class Meta:
        model = Orden
        fields = ['codigo', 'estado', 'creado_en', 'total', 'items']