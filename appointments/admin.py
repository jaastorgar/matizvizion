from django.contrib import admin
from . import models


@admin.register(models.Tecnologo)
class TecnologoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sucursal', 'especialidad', 'activo')
    list_filter = ('sucursal', 'activo')
    search_fields = ('nombre', 'rut')
    list_editable = ('activo',)


@admin.register(models.BloqueHorario)
class BloqueHorarioAdmin(admin.ModelAdmin):
    list_display = ('tecnologo', 'fecha', 'hora_inicio', 'hora_fin', 'disponible')
    list_filter = ('disponible', 'fecha', 'tecnologo__sucursal')
    list_editable = ('disponible',)
    search_fields = ('tecnologo__nombre',)


@admin.register(models.CitaMedica)
class CitaMedicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'bloque', 'estado', 'fecha_reserva')
    list_filter = ('estado',)
    search_fields = ('cliente__email',)
    actions = ['completar', 'cancelar']

    def completar(self, request, queryset):
        for c in queryset:
            if c.estado not in ('COMPLETADA', 'CANCELADA'):
                c.estado = 'COMPLETADA'; c.save(update_fields=['estado'])
        self.message_user(request, 'Citas completadas.')
    completar.short_description = 'Marcar como completada'

    def cancelar(self, request, queryset):
        for c in queryset:
            try:
                c.cancelar()
            except Exception:
                pass
        self.message_user(request, 'Citas canceladas y bloques liberados.')
    cancelar.short_description = 'Cancelar y liberar bloque'