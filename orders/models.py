import random
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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


class TipoLente(models.TextChoices):
    MONOFOCAL = 'MONOFOCAL', 'Monofocal (foco unico)'
    BIFOCAL = 'BIFOCAL', 'Bifocal (doble foco)'
    PROGRESIVO = 'PROGRESIVO', 'Progresivo / multifocal'
    OCUPACIONAL = 'OCUPACIONAL', 'Ocupacional / degresivo'


class UsoLente(models.TextChoices):
    LEJOS = 'LEJOS', 'Vision lejos'
    CERCA = 'CERCA', 'Vision cerca (lectura)'
    LEJOS_CERCA = 'LEJOS_CERCA', 'Lejos y cerca'
    INTERMEDIA = 'INTERMEDIA', 'Intermedia (pantallas 40 cm - 2 m)'


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
    tipo_lente = models.CharField('Tipo de lente', max_length=16, choices=TipoLente.choices, blank=True, default='')
    uso_lente = models.CharField('Uso / distancia', max_length=16, choices=UsoLente.choices, blank=True, default='')

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
    modo_pago = models.CharField(
        'Modalidad de pago', max_length=10,
        choices=[('COMPLETO', 'Pago completo'), ('ABONO', 'Abono 50% + saldo en tienda')],
        default='COMPLETO'
    )
    monto_abonado = models.DecimalField('Monto abonado online', max_digits=10, decimal_places=2, default=0)
    saldo_cancelado = models.BooleanField('Saldo cancelado en tienda', default=False)
    saldo_cancelado_en = models.DateTimeField('Fecha de cancelacion del saldo', null=True, blank=True)
    fecha_entrega = models.DateField(
        'Fecha de entrega', null=True, blank=True,
        help_text='Se sella automaticamente al pasar a ENTREGADA. Ancla el reloj de garantias.'
    )
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

    @property
    def saldo_pendiente(self):
        from decimal import Decimal
        if self.modo_pago != 'ABONO' or self.saldo_cancelado:
            return Decimal('0')
        return max(self.total - (self.monto_abonado or Decimal('0')), Decimal('0'))

    def _generar_codigo(self):
        for _ in range(10):
            cand = f"MV-{self.creado_en.year}-{random.randint(10000, 99999)}"
            if not Orden.objects.filter(codigo=cand).exclude(pk=self.pk).exists():
                return cand
        return f"MV-{self.creado_en.year}-{uuid.uuid4().hex[:5].upper()}"

    def save(self, *args, **kwargs):
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
        fields = ['estado', 'actualizado_en']
        if nuevo_estado == self.Estado.ENTREGADA and self.fecha_entrega is None:
            self.fecha_entrega = timezone.localdate()
            fields.append('fecha_entrega')
        self.save(update_fields=fields)
        HistorialEstado.objects.create(
            orden=self, estado_anterior=estado_anterior, estado_nuevo=nuevo_estado, usuario=usuario
        )

    def revertir_stock(self):
        from django.db.models import F
        from store.models import Producto
        for it in self.items.select_related('producto').all():
            Producto.objects.filter(pk=it.producto_id).update(stock=F('stock') + it.cantidad)


class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('store.Producto', on_delete=models.PROTECT)
    precio_unitario = models.DecimalField('Precio unitario', max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    tipo_lente = models.CharField('Tipo de lente', max_length=16, choices=TipoLente.choices, blank=True, default='')
    uso_lente = models.CharField('Uso / distancia', max_length=16, choices=UsoLente.choices, blank=True, default='')

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


class ResolucionDevolucion(models.TextChoices):
    DEVOLUCION = 'devolucion', 'Devolucion del dinero'
    CAMBIO = 'cambio', 'Cambio directo'
    REPARACION = 'reparacion', 'Reparacion gratuita'
    REHACER = 'rehacer', 'Re-hacer (multifocal)'


class SolicitudDevolucion(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='devoluciones')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitudes_devolucion')
    # Productos concretos que el cliente devuelve (lineas completas de la orden).
    items = models.ManyToManyField(
        ItemOrden, blank=True, related_name='devoluciones',
        help_text='Lineas de la orden que se devuelven. Vacio en solicitudes legacy.'
    )
    motivo = models.TextField('Motivo del cliente')
    estado = models.CharField('Estado', max_length=12, choices=EstadoDevolucion.choices, default=EstadoDevolucion.PENDIENTE, db_index=True)
    resolucion = models.CharField(
        'Resolucion aplicada', max_length=16, choices=ResolucionDevolucion.choices,
        blank=True, null=True,
        help_text='Solo "devolucion" repone stock; la orden pasa a DEVUELTA solo si se devuelven todas sus lineas.'
    )
    garantia_aplicada = models.CharField('Garantia aplicada (codigo de politica)', max_length=40, blank=True, null=True)
    motivo_rechazo = models.TextField('Motivo de rechazo (vendedor)', blank=True, null=True)
    reembolso_procesado = models.BooleanField('Reembolso procesado (manual)', default=False)
    cantidades = models.JSONField(
        'Cantidades devueltas por linea (item_id -> cantidad)',
        default=dict, blank=True,
        help_text='Vacio = devolucion de la linea completa (legado).',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    resuelto_en = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='devoluciones_resueltas')

    class Meta:
        verbose_name = 'Solicitud de devolucion'
        verbose_name_plural = 'Solicitudes de devolucion'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Devolucion #{self.id} orden {self.orden_id} [{self.estado}]"

    def cantidad_de(self, item):
        """Cantidad devuelta de una linea (parcial si existe en cantidades)."""
        try:
            return int(self.cantidades.get(str(item.id), item.cantidad))
        except Exception:
            return item.cantidad

    def revertir_stock_items(self):
        """Repone al inventario SOLO los productos/cantidades de esta solicitud."""
        from django.db.models import F
        from store.models import Producto
        for it in self.items.select_related('producto').all():
            qty = self.cantidad_de(it)
            Producto.objects.filter(pk=it.producto_id).update(stock=F('stock') + qty)


class PoliticaGarantia(models.Model):
    BASE_LEGAL = 'LEGAL'
    BASE_FABRICANTE = 'FABRICANTE'
    BASE_CONFORT = 'CONFORT'
    BASE_CHOICES = [
        (BASE_LEGAL, 'Garantía legal'),
        (BASE_FABRICANTE, 'Técnica / fabricante'),
        (BASE_CONFORT, 'Adaptación / confort'),
    ]

    codigo = models.CharField('Código interno', max_length=40, unique=True)
    nombre = models.CharField('Nombre', max_length=120)
    base = models.CharField('Base', max_length=20, choices=BASE_CHOICES, db_index=True)
    descripcion = models.TextField('Cobertura')
    exclusiones = models.TextField('Exclusiones', blank=True)
    plazo_label = models.CharField('Plazo (texto)', max_length=40)
    plazo_dias_min = models.PositiveIntegerField('Plazo mínimo (días)')
    plazo_dias_max = models.PositiveIntegerField('Plazo máximo (días)')
    activa = models.BooleanField('Activa', default=True, db_index=True)
    orden_prioridad = models.PositiveIntegerField('Orden', default=0)
    permite_devolucion = models.BooleanField('Permite devolución', default=False)
    permite_cambio = models.BooleanField('Permite cambio', default=False)
    permite_reparacion = models.BooleanField('Permite reparación', default=False)
    permite_rehacer = models.BooleanField('Permite re-hacer (multifocal)', default=False)
    solo_con_receta = models.BooleanField('Solo con receta óptica', default=False)
    categorias = models.ManyToManyField('store.Categoria', blank=True, related_name='politicas_garantia')

    class Meta:
        verbose_name = 'Política de garantía'
        verbose_name_plural = 'Políticas de garantía'
        ordering = ['orden_prioridad', 'nombre']

    def __str__(self):
        return f"{self.nombre} [{self.get_base_display()}]"


# ---- Signal: mail cuando cambia el ESTADO de una orden ----
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
        return
    prev = getattr(instance, '_prev_estado', None)
    if prev is None or prev == instance.estado:
        return
    estado = instance.estado
    oid = instance.pk
    _tx.on_commit(lambda: _enviar_mail_orden(oid, estado))