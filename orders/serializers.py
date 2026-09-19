from rest_framework import serializers
from .models import Carrito, ItemCarrito, Orden, ItemOrden, HistorialEstado


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.sku')
    precio_unitario = serializers.ReadOnlyField(source='producto.precio')
    subtotal = serializers.ReadOnlyField()
    tipo_lente_display = serializers.ReadOnlyField(source='get_tipo_lente_display')
    uso_lente_display = serializers.ReadOnlyField(source='get_uso_lente_display')

    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'producto_nombre', 'producto_sku', 'precio_unitario', 'cantidad', 'subtotal', 'tipo_lente', 'uso_lente', 'tipo_lente_display', 'uso_lente_display']


    MATRIZ_USO_LENTE = {
        'MONOFOCAL': ['LEJOS', 'CERCA'],
        'BIFOCAL': ['LEJOS_CERCA'],
        'PROGRESIVO': ['LEJOS_CERCA'],
        'OCUPACIONAL': ['INTERMEDIA', 'CERCA'],
    }

    def validate(self, attrs):
        tipo = attrs.get('tipo_lente', getattr(self.instance, 'tipo_lente', ''))
        uso = attrs.get('uso_lente', getattr(self.instance, 'uso_lente', ''))
        if tipo and uso and tipo in self.MATRIZ_USO_LENTE and uso not in self.MATRIZ_USO_LENTE[tipo]:
            raise serializers.ValidationError({'uso_lente': 'Combinacion no valida para ese tipo de lente.'})
        return attrs

class ItemOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.sku')
    subtotal = serializers.ReadOnlyField()
    tipo_lente_display = serializers.ReadOnlyField(source='get_tipo_lente_display')
    uso_lente_display = serializers.ReadOnlyField(source='get_uso_lente_display')

    class Meta:
        model = ItemOrden
        fields = ['id', 'producto', 'producto_nombre', 'producto_sku', 'precio_unitario', 'cantidad', 'subtotal', 'tipo_lente', 'uso_lente', 'tipo_lente_display', 'uso_lente_display']


class HistorialEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEstado
        fields = ['id', 'estado_anterior', 'estado_nuevo', 'cambiado_en']


class OrdenSerializer(serializers.ModelSerializer):
    cliente_email = serializers.ReadOnlyField(source='cliente.email')
    cliente_rut = serializers.SerializerMethodField()
    items = ItemOrdenSerializer(many=True, read_only=True)
    historial = HistorialEstadoSerializer(many=True, read_only=True)
    cliente_telefono = serializers.SerializerMethodField()

    def get_cliente_telefono(self, obj):
        pc = getattr(obj.cliente, 'perfil_cliente', None)
        return (getattr(pc, 'telefono', '') or getattr(obj.cliente, 'telefono', '') or '')
    saldo_pendiente = serializers.ReadOnlyField()

    class Meta:
        model = Orden
        fields = [
            'id', 'codigo', 'cliente', 'cliente_email', 'cliente_rut',
            'total', 'estado', 'creado_en', 'items', 'historial',
        'cliente_telefono', 'modo_pago', 'monto_abonado', 'saldo_cancelado', 'saldo_pendiente',
        ]
        read_only_fields = ['id', 'codigo', 'cliente', 'cliente_email', 'cliente_rut', 'total', 'estado', 'creado_en', 'items', 'historial', 'modo_pago', 'monto_abonado', 'saldo_cancelado', 'saldo_pendiente']

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