from decimal import Decimal

from django.conf import settings
from django.db import models


class EstadoOrden(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PAGADA = 'PAGADA', 'Pagada'
    EN_PREPARACION = 'EN_PREPARACION', 'En preparación'
    ENVIADA = 'ENVIADA', 'Enviada'
    ENTREGADA = 'ENTREGADA', 'Entregada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    FALLIDA = 'FALLIDA', 'Fallida'


class Carrito(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carritos'
    )
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
        return sum(
            (item.subtotal for item in self.items.all()),
            Decimal('0')
        )


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name='items'
    )
    producto = models.ForeignKey(
        'store.Producto',
        on_delete=models.CASCADE
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Item de carrito'
        verbose_name_plural = 'Items de carrito'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name='item_carrito_cantidad_positiva'
            )
        ]

    def __str__(self):
        return f"Item carrito #{self.id} - Producto #{self.producto_id}"

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad


class Orden(models.Model):
    Estado = EstadoOrden

    ESTADOS = Estado.choices

    TRANSICIONES_PERMITIDAS = {
        Estado.PENDIENTE: [
            Estado.PAGADA,
            Estado.CANCELADA,
            Estado.FALLIDA,
        ],
        Estado.PAGADA: [
            Estado.EN_PREPARACION,
            Estado.CANCELADA,
        ],
        Estado.EN_PREPARACION: [
            Estado.ENVIADA,
            Estado.CANCELADA,
        ],
        Estado.ENVIADA: [
            Estado.ENTREGADA,
        ],
        Estado.ENTREGADA: [],
        Estado.CANCELADA: [],
        Estado.FALLIDA: [],
    }

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ordenes'
    )
    total = models.DecimalField(
        'Total',
        max_digits=10,
        decimal_places=2
    )
    estado = models.CharField(
        'Estado',
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-creado_en']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoOrden.values),
                name='orden_estado_valido'
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name='orden_total_no_negativo'
            )
        ]

    def __str__(self):
        return f"Orden #{self.id} - {self.cliente}"

    def puede_cambiar_a(self, nuevo_estado):
        return nuevo_estado in self.TRANSICIONES_PERMITIDAS.get(self.estado, [])

    def cambiar_estado(self, nuevo_estado, usuario=None):
        if not self.puede_cambiar_a(nuevo_estado):
            raise ValueError(
                f"No se puede cambiar la orden de {self.estado} a {nuevo_estado}."
            )

        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save(update_fields=['estado', 'actualizado_en'])

        HistorialEstado.objects.create(
            orden=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario
        )


class ItemOrden(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='items'
    )
    producto = models.ForeignKey(
        'store.Producto',
        on_delete=models.PROTECT
    )
    precio_unitario = models.DecimalField(
        'Precio unitario',
        max_digits=10,
        decimal_places=2
    )
    cantidad = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Item de orden'
        verbose_name_plural = 'Items de orden'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name='item_orden_cantidad_positiva'
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name='item_orden_precio_no_negativo'
            )
        ]

    def __str__(self):
        return f"Item orden #{self.id} - Producto #{self.producto_id}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class HistorialEstado(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    estado_anterior = models.CharField(
        max_length=20,
        blank=True
    )
    estado_nuevo = models.CharField(
        max_length=20,
        choices=EstadoOrden.choices
    )
    cambiado_en = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales_estado'
    )

    class Meta:
        verbose_name = 'Historial de estado'
        verbose_name_plural = 'Historiales de estado'
        ordering = ['-cambiado_en']

    def __str__(self):
        return f"Historial Orden #{self.orden_id}: {self.estado_anterior} -> {self.estado_nuevo}"