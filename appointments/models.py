from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EstadoCita(models.TextChoices):
    AGENDADA = 'AGENDADA', 'Agendada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    COMPLETADA = 'COMPLETADA', 'Completada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    NO_ASISTIO = 'NO_ASISTIO', 'No Asistió'


class Tecnologo(models.Model):
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE, related_name='tecnologos', db_index=True)
    nombre = models.CharField('Nombre completo', max_length=150)
    rut = models.CharField('RUT', max_length=12, unique=True)
    especialidad = models.CharField('Especialidad', max_length=100)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Tecnólogo'
        verbose_name_plural = 'Tecnólogos'
        ordering = ['nombre']

    @staticmethod
    def normalizar_rut(rut):
        if not rut:
            return rut
        return rut.strip().upper().replace('.', '').replace('-', '').replace(' ', '')

    def clean(self):
        super().clean()
        self.rut = self.normalizar_rut(self.rut)

    def save(self, *args, **kwargs):
        self.rut = self.normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class BloqueHorario(models.Model):
    tecnologo = models.ForeignKey(Tecnologo, on_delete=models.CASCADE, related_name='bloques')
    fecha = models.DateField('Fecha', db_index=True)
    hora_inicio = models.TimeField('Hora de inicio')
    hora_fin = models.TimeField('Hora de fin')
    disponible = models.BooleanField('Disponible', default=True, db_index=True)

    class Meta:
        verbose_name = 'Bloque horario'
        verbose_name_plural = 'Bloques horarios'
        ordering = ['fecha', 'hora_inicio']
        constraints = [
            models.UniqueConstraint(fields=['tecnologo', 'fecha', 'hora_inicio'], name='bloque_unico_tecnologo_fecha_inicio')
        ]

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')
        if self.tecnologo_id and self.fecha and self.hora_inicio and self.hora_fin:
            solapados = BloqueHorario.objects.filter(
                tecnologo=self.tecnologo, fecha=self.fecha,
                hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio,
            )
            if self.pk:
                solapados = solapados.exclude(pk=self.pk)
            if solapados.exists():
                raise ValidationError('Este bloque se solapa con otro ya existente del mismo tecnólogo.')

    def __str__(self):
        return f"{self.fecha} {self.hora_inicio}-{self.hora_fin} | {self.tecnologo.nombre}"


class CitaMedica(models.Model):
    Estado = EstadoCita
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas')
    bloque = models.OneToOneField(BloqueHorario, on_delete=models.PROTECT, related_name='cita')
    estado = models.CharField('Estado', max_length=20, choices=EstadoCita.choices, default=EstadoCita.AGENDADA, db_index=True)
    fecha_reserva = models.DateTimeField('Fecha de reserva', auto_now_add=True)

    class Meta:
        verbose_name = 'Cita médica'
        verbose_name_plural = 'Citas médicas'
        ordering = ['-fecha_reserva']
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=EstadoCita.values), name='cita_estado_valido')
        ]

    def __str__(self):
        return f"Cita #{self.id}: {self.cliente.email} - {self.bloque}"

    def save(self, *args, **kwargs):
        if self.pk:
            self._prev_estado = CitaMedica.objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        super().save(*args, **kwargs)

    def cancelar(self):
        if self.estado == EstadoCita.COMPLETADA:
            raise ValidationError('No se puede cancelar una cita ya completada.')
        if self.estado == EstadoCita.CANCELADA:
            return
        self.estado = EstadoCita.CANCELADA
        self.save(update_fields=['estado'])
        bloque = self.bloque
        bloque.disponible = True
        bloque.save(update_fields=['disponible'])


# ---- Signal: mail en alta (agendada) y en cambios de estado (cancelada/completada) ----
from django.db import transaction as _tx
from django.db.models.signals import post_save as _post_save_cita
from django.dispatch import receiver as _receiver_cita


def _enviar_mail_cita(cita_id, evento):
    from core.notifications import notify_cita
    try:
        c = CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal').get(pk=cita_id)
        notify_cita(c, evento)
    except CitaMedica.DoesNotExist:
        pass


@_receiver_cita(_post_save_cita, sender=CitaMedica)
def _cita_mail(sender, instance, created, **kwargs):
    if created:
        evento = 'agendada'
    else:
        prev = getattr(instance, '_prev_estado', None)
        if prev is None or prev == instance.estado:
            return
        evento = {'CANCELADA': 'cancelada', 'COMPLETADA': 'completada'}.get(instance.estado)
        if not evento:
            return
    cid = instance.pk
    _tx.on_commit(lambda: _enviar_mail_cita(cid, evento))