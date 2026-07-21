from django.contrib import admin

from .models import LogPago, TransaccionWebpay


class LogPagoInline(admin.TabularInline):
    model = LogPago
    extra = 0
    fields = (
        'evento',
        'fecha_registro',
    )
    readonly_fields = (
        'evento',
        'fecha_registro',
    )
    ordering = ('-fecha_registro',)


@admin.register(TransaccionWebpay)
class TransaccionWebpayAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'orden',
        'buy_order',
        'amount',
        'status',
        'response_code',
        'authorization_code',
        'creado_en',
    )
    list_filter = (
        'status',
        'creado_en',
    )
    search_fields = (
        'orden__id',
        'buy_order',
        'session_id',
        'token',
        'authorization_code',
    )
    readonly_fields = (
        'orden',
        'buy_order',
        'session_id',
        'token',
        'amount',
        'status',
        'response_code',
        'authorization_code',
        'payment_type_code',
        'installments_number',
        'installments_amount',
        'creado_en',
        'actualizado_en',
    )
    inlines = [
        LogPagoInline,
    ]


@admin.register(LogPago)
class LogPagoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'transaccion',
        'evento',
        'fecha_registro',
    )
    list_filter = (
        'evento',
        'fecha_registro',
    )
    search_fields = (
        'transaccion__buy_order',
        'transaccion__token',
    )
    readonly_fields = (
        'transaccion',
        'evento',
        'raw_response',
        'fecha_registro',
    )