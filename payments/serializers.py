from rest_framework import serializers

from .models import LogPago, TransaccionWebpay


class TransaccionWebpaySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransaccionWebpay
        fields = ['id', 'orden', 'buy_order', 'session_id', 'token', 'amount', 'status']
        read_only_fields = fields


class LogPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogPago
        fields = ['id', 'transaccion', 'raw_response', 'fecha_registro']
        read_only_fields = fields


class WebpayCreateSerializer(serializers.Serializer):
    orden_id = serializers.IntegerField(required=True)


class WebpayReturnSerializer(serializers.Serializer):
    token_ws = serializers.CharField(max_length=255, required=True)