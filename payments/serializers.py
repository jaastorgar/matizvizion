from rest_framework import serializers

from .models import LogPago, TransaccionWebpay


class TransaccionWebpaySerializer(serializers.ModelSerializer):
    orden_id = serializers.IntegerField(
        source='orden.id',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = TransaccionWebpay
        fields = [
            'id',
            'orden_id',
            'buy_order',
            'session_id',
            'amount',
            'status',
            'status_display',
            'response_code',
            'authorization_code',
            'payment_type_code',
            'installments_number',
            'installments_amount',
            'creado_en',
            'actualizado_en',
        ]
        read_only_fields = [
            'id',
            'orden_id',
            'buy_order',
            'session_id',
            'amount',
            'status',
            'status_display',
            'response_code',
            'authorization_code',
            'payment_type_code',
            'installments_number',
            'installments_amount',
            'creado_en',
            'actualizado_en',
        ]


class LogPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogPago
        fields = [
            'id',
            'transaccion',
            'evento',
            'fecha_registro',
        ]
        read_only_fields = [
            'id',
            'transaccion',
            'evento',
            'fecha_registro',
        ]


class WebpayCreateSerializer(serializers.Serializer):
    """
    Valida la recepción del ID de la orden desde el frontend.
    """
    orden_id = serializers.IntegerField(required=True)


class WebpayReturnSerializer(serializers.Serializer):
    """
    Valida la recepción del token_ws desde Transbank o frontend.
    """
    token_ws = serializers.CharField(max_length=255, required=True)