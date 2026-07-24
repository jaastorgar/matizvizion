import random
import uuid

from django.conf import settings
from django.db import models


class EstadoOrden(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PAGADA = 'PAGADA', 'Pagada'
    EN_PREPARACION = 'EN_PREPARACION', 'En preparacion'
    LISTO_PARA_RETIRO = 'LISTO_PARA_RETIRO', 'Listo para retiro'
    ENVIADA = 'ENVIADA', 'Enviada'
    ENTREGADA = 'ENTREGADA', 'Entregada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    FALLIDA = 'FALLIDA', 'Fallida'
    DEVUELTA = 'DEVUELTA', 'Devuelta'


class Carrito(models.Model):
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carritos')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Carrito #{self.id} - {self.cliente}"

    @property
    def total(self):
        from decimal import Decimal
        return sum((it.subtotal for it in self.items.all()), Decimal('0'))


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('store.Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Item de carrito'
        verbose_name_plural = 'Items de carrito'
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='item_carrito_cantidad_positiva')]

    def __str__(self):
        return f"Item carrito #{self.id} - Producto #{self.producto_id}"

    @property
    def subtotal(self):
        return (self.producto.precio or 0) * (self.cantidad or 0)


class Orden(models.Model):
    Estado = EstadoOrden
    ESTADOS = Estado.choices

    TRANSICIONES_PERMITIDAS = {
        Estado.PENDIENTE: [Estado.PAGADA, Estado.CANCELADA, Estado.FALLIDA],
        Estado.PAGADA: [Estado.EN_PREPARACION, Estado.CANCELADA],
        Estado.EN_PREPARACION: [Estado.LISTO_PARA_RETIRO, Estado.ENVIADA, Estado.CANCELADA],
        Estado.LISTO_PARA_RETIRO: [Estado.ENTREGADA, Estado.CANCELADA],
        Estado.ENVIADA: [Estado.ENTREGADA, Estado.DEVUELTA],
        Estado.ENTREGADA: [Estado.DEVUELTA],
        Estado.CANCELADA: [],
        Estado.FALLIDA: [],
        Estado.DEVUELTA: [],
    }

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordenes')
    codigo = models.CharField(
        'Codigo de pedido', max_length=20, unique=True, null=True, blank=True,
        help_text='Codigo legible y no secuencial (ej. MV-2026-48271). Se autogenera.'
    )
    total = models.DecimalField('Total', max_digits=10, decimal_places=2)
    estado = models.CharField('Estado', max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Ordenes'
        ordering = ['-creado_en']
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=EstadoOrden.values), name='orden_estado_valido'),
            models.CheckConstraint(condition=models.Q(total__gte=0), name='orden_total_no_negativo'),
        ]

    def __str__(self):
        return f"{self.codigo or ('Orden #' + str(self.id))} - {self.cliente}"

    def _generar_codigo(self):
        for _ in range(10):
            cand = f"MV-{self.creado_en.year}-{random.randint(10000, 99999)}"
            if not Orden.objects.filter(codigo=cand).exclude(pk=self.pk).exists():
                return cand
        return f"MV-{self.creado_en.year}-{uuid.uuid4().hex[:5].upper()}"

    def save(self, *args, **kwargs):
        # Captura el estado previo (si ya existe) para que la signal detecte cambios
        if self.pk:
            self._prev_estado = Orden.objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = self._generar_codigo()
            super().save(update_fields=['codigo'])

    def puede_cambiar_a(self, nuevo_estado):
        return nuevo_estado in self.TRANSICIONES_PERMITIDAS.get(self.estado, [])

    def cambiar_estado(self, nuevo_estado, usuario=None):
        if not self.puede_cambiar_a(nuevo_estado):
            raise ValueError(f"No se puede cambiar la orden de {self.estado} a {nuevo_estado}.")
        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save(update_fields=['estado', 'actualizado_en'])
        HistorialEstado.objects.create(
            orden=self, estado_anterior=estado_anterior, estado_nuevo=nuevo_estado, usuario=usuario
        )

    def revertir_stock(self):
        """Devuelve al inventario los productos de la orden. Llamar dentro de transaction.atomic."""
        from django.db.models import F
        from store.models import Producto
        for it in self.items.select_related('producto').all():
            Producto.objects.filter(pk=it.producto_id).update(stock=F('stock') + it.cantidad)


class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('store.Producto', on_delete=models.PROTECT)
    precio_unitario = models.DecimalField('Precio unitario', max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Item de orden'
        verbose_name_plural = 'Items de orden'
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='item_orden_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gte=0), name='item_orden_precio_no_negativo'),
        ]

    def __str__(self):
        return f"Item orden #{self.id} - Producto #{self.producto_id}"

    @property
    def subtotal(self):
        return (self.precio_unitario or 0) * (self.cantidad or 0)


class HistorialEstado(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=EstadoOrden.choices)
    cambiado_en = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='historiales_estado'
    )

    class Meta:
        verbose_name = 'Historial de estado'
        verbose_name_plural = 'Historiales de estado'
        ordering = ['-cambiado_en']

    def __str__(self):
        return f"Historial Orden #{self.orden_id}: {self.estado_anterior} -> {self.estado_nuevo}"


class EstadoDevolucion(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    APROBADA = 'APROBADA', 'Aprobada'
    RECHAZADA = 'RECHAZADA', 'Rechazada'


class SolicitudDevolucion(models.Model):
    """
    Devolucion por garantia de satisfaccion. El cliente SOLICITA; el vendedor
    APRUEBA cuando el cliente entrega el producto en tienda (ahi se devuelve
    el stock y la orden pasa a DEVUELTA). No es autoservicio por seguridad.
    """
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='devoluciones')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitudes_devolucion')
    motivo = models.TextField('Motivo del cliente')
    estado = models.CharField('Estado', max_length=12, choices=EstadoDevolucion.choices, default=EstadoDevolucion.PENDIENTE, db_index=True)
    motivo_rechazo = models.TextField('Motivo de rechazo (vendedor)', blank=True, null=True)
    reembolso_procesado = models.BooleanField('Reembolso procesado (manual)', default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    resuelto_en = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='devoluciones_resueltas')

    class Meta:
        verbose_name = 'Solicitud de devolucion'
        verbose_name_plural = 'Solicitudes de devolucion'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Devolucion #{self.id} orden {self.orden_id} [{self.estado}]"


# ---- Signal: mail cuando cambia el ESTADO de una orden (cualquiera sea el origen) ----
from django.db import transaction as _tx
from django.db.models.signals import post_save as _post_save_orden
from django.dispatch import receiver as _receiver_orden


def _enviar_mail_orden(orden_id, estado):
    from core.notifications import notify_orden
    try:
        o = Orden.objects.prefetch_related('items__producto').select_related('cliente').get(pk=orden_id)
        notify_orden(o, estado)
    except Orden.DoesNotExist:
        pass


@_receiver_orden(_post_save_orden, sender=Orden)
def _orden_estado_mail(sender, instance, created, **kwargs):
    if created:
        return  # PENDIENTE inicial no manda mail
    prev = getattr(instance, '_prev_estado', None)
    if prev is None or prev == instance.estado:
        return
    estado = instance.estado
    oid = instance.pk
    _tx.on_commit(lambda: _enviar_mail_orden(oid, estado))