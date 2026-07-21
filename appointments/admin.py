from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import BloqueHorario, CitaMedica, EstadoCita, Tecnologo


@admin.register(Tecnologo)
class TecnologoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'especialidad', 'sucursal', 'activo')
    list_filter = ('activo', 'sucursal', 'especialidad')
    search_fields = ('nombre', 'rut', 'especialidad')
    list_select_related = ('sucursal',)

    def save_model(self, request, obj, form, change):
        # Ejecuta clean() del modelo (normaliza RUT y valida) antes de guardar
        try:
            obj.full_clean()
        except ValidationError as error:
            messages.error(request, '; '.join(error.messages))
            return
        super().save_model(request, obj, form, change)


@admin.register(BloqueHorario)
class BloqueHorarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'tecnologo', 'disponible')
    list_filter = ('disponible', 'fecha', 'tecnologo__sucursal')
    search_fields = ('tecnologo__nombre',)
    list_select_related = ('tecnologo__sucursal',)
    date_hierarchy = 'fecha'

    def save_model(self, request, obj, form, change):
        # Ejecuta clean(): valida horas y solapamiento antes de guardar
        try:
            obj.full_clean()
        except ValidationError as error:
            messages.error(request, '; '.join(error.messages))
            return
        super().save_model(request, obj, form, change)


@admin.register(CitaMedica)
class CitaMedicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'bloque', 'tecnologo', 'estado', 'fecha_reserva')
    list_filter = ('estado', 'fecha_reserva', 'bloque__tecnologo__sucursal')
    search_fields = ('cliente__email', 'bloque__tecnologo__nombre')
    list_select_related = ('cliente', 'bloque__tecnologo__sucursal')
    readonly_fields = ('cliente', 'bloque', 'fecha_reserva')
    actions = ['marcar_completada', 'marcar_cancelada']

    def tecnologo(self, obj):
        return obj.bloque.tecnologo.nombre
    tecnologo.short_description = 'Tecnólogo'

    @admin.action(description='Marcar citas seleccionadas como COMPLETADA')
    def marcar_completada(self, request, queryset):
        for cita in queryset:
            if cita.estado != EstadoCita.CANCELADA:
                cita.estado = EstadoCita.COMPLETADA
                cita.save(update_fields=['estado'])

    @admin.action(description='Cancelar citas seleccionadas (libera el bloque)')
    def marcar_cancelada(self, request, queryset):
        for cita in queryset:
            try:
                cita.cancelar()
            except ValidationError as error:
                messages.warning(request, f"Cita #{cita.id}: {error.message}")