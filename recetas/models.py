from django.db import models
from django.conf import settings
from django.utils import timezone


import os
import uuid

def receta_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    token = uuid.uuid4().hex
    return f"recetas/{instance.cliente_id or 'anon'}/{token[:4]}/{token}{ext}"


class Receta(models.Model):
    class Tipo(models.TextChoices):
        OPTICA = 'OPTICA', 'Receta de lentes (optica)'
        CONTACTOLOGIA = 'CONTACTOLOGIA', 'Receta de lentes de contacto'
        OTRO = 'OTRO', 'Otro documento visual'

    class Estado(models.TextChoices):
        VIGENTE = 'VIGENTE', 'Vigente'
        VENCIDA = 'VENCIDA', 'Vencida'
        SIN_FECHA = 'SIN_FECHA', 'Sin fecha de vigencia'

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recetas')
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.OPTICA)
    archivo = models.FileField(upload_to=receta_upload_path)
    nombre = models.CharField(max_length=120, blank=True, default='')
    detalle = models.TextField(blank=True, default='')
    vigencia_hasta = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True, default='')
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='recetas_subidas')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'receta'
        verbose_name_plural = 'recetas'

    def __str__(self):
        return 'Receta %s - cliente %s (%s)' % (self.pk, self.cliente_id, self.get_tipo_display())

    @property
    def estado(self):
        if not self.vigencia_hasta:
            return self.Estado.SIN_FECHA
        return self.Estado.VIGENTE if self.vigencia_hasta >= timezone.localdate() else self.Estado.VENCIDA
