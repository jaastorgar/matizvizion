from django.contrib import admin
from . import models


class ItemOrdenInline(admin.TabularInline):
    model = models.ItemOrden
    extra = 0


@admin.register(models.Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'cliente', 'estado', 'total', 'creado_en')
    list_filter = ('estado',)
    search_fields = ('codigo', 'cliente__email')
    inlines = (ItemOrdenInline,)
    readonly_fields = ('codigo', 'creado_en', 'actualizado_en')
    actions = ['marcar_entregada']

    def marcar_entregada(self, request, queryset):
        n = 0
        for o in queryset:
            if o.puede_cambiar_a(models.EstadoOrden.ENTREGADA):
                o.cambiar_estado(models.EstadoOrden.ENTREGADA, usuario=request.user)
                n += 1
        self.message_user(request, f'{n} orden(es) marcadas como entregadas.')
    marcar_entregada.short_description = 'Marcar como entregada'


@admin.register(models.Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'actualizado_en')
    search_fields = ('cliente__email',)


@admin.register(models.HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('orden', 'estado_anterior', 'estado_nuevo', 'cambiado_en', 'usuario')
    list_filter = ('estado_nuevo',)
    readonly_fields = ('orden', 'estado_anterior', 'estado_nuevo', 'cambiado_en', 'usuario')


if hasattr(models, 'SolicitudDevolucion'):
    @admin.register(models.SolicitudDevolucion)
    class SolicitudDevolucionAdmin(admin.ModelAdmin):
        list_display = ('id', 'orden', 'cliente', 'estado', 'creado_en')
        list_filter = ('estado',)
        search_fields = ('orden__codigo', 'cliente__email')
        readonly_fields = ('creado_en',)


if hasattr(models, 'PoliticaGarantia'):
    @admin.register(models.PoliticaGarantia)
    class PoliticaGarantiaAdmin(admin.ModelAdmin):
        list_display = ('nombre', 'base', 'plazo_label', 'activa', 'orden_prioridad')
        list_filter = ('base', 'activa')
        list_editable = ('activa', 'orden_prioridad')
        search_fields = ('nombre', 'codigo')