from django.db import models


class Sucursal(models.Model):
    """
    Sucursal física de Óptica Matiz Visión.
    """
    nombre = models.CharField(
        'Nombre de sucursal',
        max_length=100
    )
    direccion = models.CharField(
        'Dirección',
        max_length=255
    )
    telefono = models.CharField(
        'Teléfono',
        max_length=20,
        blank=True
    )
    activa = models.BooleanField(
        'Activa',
        default=True
    )
    created_at = models.DateTimeField(
        'Creado',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Actualizado',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre