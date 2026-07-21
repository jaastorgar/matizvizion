from django.db import models

from orders.models import Orden


class EstadoTransaccion(models.TextChoices):
    INICIADA = 'INICIADA', 'Iniciada'
    AUTHORIZED = 'AUTHORIZED', 'Autorizada'
    RECHAZADA = 'RECHAZADA', 'Rechazada'
    FALLIDA = 'FALLIDA', 'Fallida'
    ERROR = 'ERROR', 'Error'
    EXPIRADA = 'EXPIRADA', 'Expirada'
    ANULADA = 'ANULADA', 'Anulada'


class TransaccionWebpay(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='transacciones'
    )
    buy_order = models.CharField(
        'Orden de compra',
        max_length=64,
        db_index=True
    )
    session_id = models.CharField(
        'ID de sesión',
        max_length=128
    )
    token = models.CharField(
        'Token WS',
        max_length=255,
        unique=True
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        'Estado Transbank',
        max_length=20,
        choices=EstadoTransaccion.choices,
        default=EstadoTransaccion.INICIADA
    )

    response_code = models.IntegerField(
        'Código de respuesta',
        null=True,
        blank=True
    )
    authorization_code = models.CharField(
        'Código de autorización',
        max_length=50,
        blank=True
    )
    payment_type_code = models.CharField(
        'Tipo de pago',
        max_length=10,
        blank=True
    )
    installments_number = models.PositiveIntegerField(
        'Número de cuotas',
        null=True,
        blank=True
    )
    installments_amount = models.DecimalField(
        'Monto de cuota',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transacción Webpay'
        verbose_name_plural = 'Transacciones Webpay'
        ordering = ['-creado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['orden'],
                condition=models.Q(status='AUTHORIZED'),
                name='unique_transaccion_autorizada_por_orden'
            )
        ]

    def __str__(self):
        return f"{self.buy_order} ({self.status})"


class LogPago(models.Model):
    class Evento(models.TextChoices):
        CREATE = 'CREATE', 'Creación de transacción'
        COMMIT = 'COMMIT', 'Confirmación de pago'
        ERROR = 'ERROR', 'Error'
        RETURN = 'RETURN', 'Retorno Webpay'

    transaccion = models.ForeignKey(
        TransaccionWebpay,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    evento = models.CharField(
        'Evento',
        max_length=20,
        choices=Evento.choices,
        default=Evento.RETURN
    )
    raw_response = models.JSONField(
        'Respuesta raw de Transbank'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de pago'
        verbose_name_plural = 'Logs de pago'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"Log {self.evento} - Transacción #{self.transaccion_id}"