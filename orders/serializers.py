from rest_framework import serializers
from .models import Carrito, ItemCarrito, Orden, ItemOrden, HistorialEstado

class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    precio_unitario = serializers.ReadOnlyField(source='producto.precio')
    subtotal = serializers.ReadOnlyField()
    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'producto_nombre', 'precio_unitario', 'cantidad', 'subtotal']

class ItemOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    subtotal = serializers.ReadOnlyField()
    class Meta:
        model = ItemOrden
        fields = ['id', 'producto', 'producto_nombre', 'precio_unitario', 'cantidad', 'subtotal']

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
        fields = ['id', 'cliente', 'cliente_email', 'cliente_rut', 'total', 'estado', 'creado_en', 'items', 'historial']
        read_only_fields = ['id', 'cliente', 'cliente_email', 'cliente_rut', 'total', 'estado', 'creado_en', 'items', 'historial']
    def get_cliente_rut(self, obj):
        try:
            return obj.cliente.perfil_cliente.rut
        except Exception:
            return None