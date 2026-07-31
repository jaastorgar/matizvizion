from datetime import date, datetime, timedelta

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import BloqueHorario, CitaMedica, Tecnologo


# ---------------------------------------------------------------------------
# Formulario del generador de agenda por slot
# ---------------------------------------------------------------------------
class GenerarSlotForm(forms.Form):
    tecnologo = forms.ModelChoiceField(
        queryset=Tecnologo.objects.filter(activo=True).select_related('sucursal'),
        label='Tecnólogo',
        help_text='Sobre qué profesional se generará la agenda.',
    )
    fecha_desde = forms.DateField(
        label='Desde', initial=date.today,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    fecha_hasta = forms.DateField(
        label='Hasta', initial=date.today,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    hora_inicio = forms.TimeField(
        label='Hora de inicio del turno', initial='09:00',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    hora_fin = forms.TimeField(
        label='Hora de fin del turno', initial='18:00',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    slot_minutes = forms.IntegerField(
        label='Duración de cada slot (min)', initial=60, min_value=15, max_value=240,
        help_text='Ej: 60 para citas de 1 hora, 30 para media hora.',
    )

    def clean(self):
        cd = super().clean()
        d1 = cd.get('fecha_desde'); d2 = cd.get('fecha_hasta')
        hi = cd.get('hora_inicio'); hf = cd.get('hora_fin')
        mins = cd.get('slot_minutes')
        if d1 and d2 and d2 < d1:
            raise forms.ValidationError('La fecha "Hasta" no puede ser anterior a "Desde".')
        if hi and hf and hf <= hi:
            raise forms.ValidationError('La hora de fin debe ser posterior a la de inicio.')
        if hi and hf and mins:
            span = (datetime.combine(date.today(), hf) - datetime.combine(date.today(), hi)).total_seconds() / 60
            if span < mins:
                raise forms.ValidationError('El turno es más corto que la duración del slot.')
        return cd


def _iter_slots(hora_inicio, hora_fin, mins):
    """Genera pares (inicio, fin) contiguos dentro de la ventana del dia."""
    step = timedelta(minutes=mins)
    base = datetime.combine(date.today(), hora_inicio)
    end = datetime.combine(date.today(), hora_fin)
    while base + step <= end:
        nxt = base + step
        yield base.time(), nxt.time()
        base = nxt


def _solapa(tecnologo, dia, hi, hf, exclude_pk=None):
    qs = BloqueHorario.objects.filter(
        tecnologo=tecnologo, fecha=dia, hora_inicio__lt=hf, hora_fin__gt=hi,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


# ---------------------------------------------------------------------------
# Admin: Tecnólogo
# ---------------------------------------------------------------------------
@admin.register(Tecnologo)
class TecnologoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sucursal', 'especialidad', 'activo')
    list_filter = ('activo', 'sucursal')
    search_fields = ('nombre', 'rut', 'especialidad')
    list_editable = ('activo',)


# ---------------------------------------------------------------------------
# Admin: Bloque horario + generador por slot
# ---------------------------------------------------------------------------
@admin.register(BloqueHorario)
class BloqueHorarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'tecnologo', 'disponible')
    list_filter = ('disponible', 'fecha', 'tecnologo__sucursal', 'tecnologo')
    search_fields = ('tecnologo__nombre',)
    date_hierarchy = 'fecha'
    list_editable = ('disponible',)
    change_list_template = 'admin/appointments/bloquehorario_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'generar-slot/',
                self.admin_site.admin_view(self.generar_slot_view),
                name='appointments_bloquehorario_generar_slot',
            ),
        ]
        return custom + urls

    def generar_slot_view(self, request):
        if request.method == 'POST':
            form = GenerarSlotForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                tec = cd['tecnologo']
                creados = actualizados = ya = omitidos = 0
                omitidos_detalle = []
                dia = cd['fecha_desde']
                while dia <= cd['fecha_hasta']:
                    for hi, hf in _iter_slots(cd['hora_inicio'], cd['hora_fin'], cd['slot_minutes']):
                        existing = BloqueHorario.objects.filter(
                            tecnologo=tec, fecha=dia, hora_inicio=hi
                        ).first()
                        if existing:
                            tiene_cita = CitaMedica.objects.filter(bloque=existing).exists()
                            mismo = (existing.hora_fin == hf and existing.disponible)
                            if mismo:
                                ya += 1
                                continue
                            if tiene_cita or _solapa(tec, dia, hi, hf, exclude_pk=existing.pk):
                                omitidos += 1
                                omitidos_detalle.append(f'{dia} {hi} (colision/cita)')
                                continue
                            existing.hora_fin = hf
                            existing.disponible = True
                            existing.save(update_fields=['hora_fin', 'disponible'])
                            actualizados += 1
                        else:
                            if _solapa(tec, dia, hi, hf):
                                omitidos += 1
                                omitidos_detalle.append(f'{dia} {hi} (colision)')
                                continue
                            BloqueHorario.objects.create(
                                tecnologo=tec, fecha=dia, hora_inicio=hi,
                                hora_fin=hf, disponible=True,
                            )
                            creados += 1
                    dia += timedelta(days=1)
                msg = (
                    f'Agenda generada para {tec.nombre}: {creados} creados, '
                    f'{actualizados} redimensionados, {ya} ya existian, {omitidos} omitidos.'
                )
                if omitidos_detalle:
                    msg += ' Omitidos: ' + ', '.join(omitidos_detalle[:8])
                    if len(omitidos_detalle) > 8:
                        msg += f' …(+{len(omitidos_detalle) - 8} mas)'
                self.message_user(request, msg, level=messages.SUCCESS)
                return redirect('..')
        else:
            form = GenerarSlotForm()

        context = {
            'form': form,
            'title': 'Generar agenda por slot',
            'opts': self.model._meta,
            'has_change_permission': True,
        }
        return render(request, 'admin/appointments/generar_slot.html', context)


# ---------------------------------------------------------------------------
# Admin: Cita médica
# ---------------------------------------------------------------------------
@admin.register(CitaMedica)
class CitaMedicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'bloque', 'estado', 'fecha_reserva')
    list_filter = ('estado', 'bloque__fecha')
    search_fields = ('cliente__email',)
    raw_id_fields = ('cliente', 'bloque')
    date_hierarchy = 'bloque__fecha'