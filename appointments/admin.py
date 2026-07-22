from django.contrib import admin
from .models import Tecnologo, BloqueHorario, CitaMedica

@admin.register(Tecnologo)
class TecnologoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'especialidad', 'sucursal')
    list_filter = ('sucursal',)
    search_fields = ('nombre', 'rut')
    list_select_related = ('sucursal',)

@admin.register(BloqueHorario)
class BloqueHorarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'tecnologo', 'disponible')
    list_filter = ('disponible', 'fecha', 'tecnologo__sucursal')
    list_select_related = ('tecnologo__sucursal',)
    date_hierarchy = 'fecha'

@admin.register(CitaMedica)
class CitaMedicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'bloque', 'estado', 'fecha_reserva')
    list_filter = ('estado',)
    list_select_related = ('cliente', 'bloque__tecnologo__sucursal')
    actions = ['marcar_cancelada', 'marcar_completada']
    def marcar_cancelada(self, request, queryset):
        for c in queryset.select_related('bloque'):
            if c.estado != 'COMPLETADA':
                c.estado = 'CANCELADA'; c.save(update_fields=['estado'])
                b = c.bloque; b.disponible = True; b.save(update_fields=['disponible'])
    marcar_cancelada.short_description = 'Cancelar citas seleccionadas (libera bloque)'
    def marcar_completada(self, request, queryset):
        for c in queryset:
            if c.estado != 'CANCELADA':
                c.estado = 'COMPLETADA'; c.save(update_fields=['estado'])
    marcar_completada.short_description = 'Completar citas seleccionadas'