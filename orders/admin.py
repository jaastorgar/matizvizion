from django.contrib import admin
from . import models


class ItemOrdenInline(admin.TabularInline):
    model = models.ItemOrden
    extra = 0


@admin.register(models.Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'cliente', 'estado', 'stock_revertido', 'total', 'creado_en')
    list_filter = ('estado', 'stock_revertido')
    search_fields = ('codigo', 'cliente__email')
    inlines = (ItemOrdenInline,)
    readonly_fields = ('codigo', 'stock_revertido', 'creado_en', 'actualizado_en')
    actions = ['marcar_entregada', 'marcar_cancelada', 'marcar_devuelta']

    def save_model(self, request, obj, form, change):
        if change and 'estado' in form.changed_data:
            prev_estado = form.initial.get('estado')
            nuevo_estado = obj.estado
            super().save_model(request, obj, form, change)
            if nuevo_estado in (models.EstadoOrden.CANCELADA, models.EstadoOrden.FALLIDA, models.EstadoOrden.DEVUELTA):
                unidades = obj.revertir_stock()
                if unidades > 0:
                    self.message_user(
                        request,
                        f"Stock devuelto automáticamente: {unidades} unidad(es) de la orden {obj.codigo} reincorporadas al inventario."
                    )
            models.HistorialEstado.objects.create(
                orden=obj,
                estado_anterior=prev_estado or '',
                estado_nuevo=nuevo_estado,
                usuario=request.user,
            )
        else:
            super().save_model(request, obj, form, change)

    def marcar_entregada(self, request, queryset):
        n = 0
        for o in queryset:
            if o.puede_cambiar_a(models.EstadoOrden.ENTREGADA):
                o.cambiar_estado(models.EstadoOrden.ENTREGADA, usuario=request.user)
                n += 1
        self.message_user(request, f'{n} orden(es) marcadas como entregadas.')
    marcar_entregada.short_description = 'Marcar como entregada'

    def marcar_cancelada(self, request, queryset):
        n = 0
        unidades = 0
        for o in queryset:
            if o.estado not in (models.EstadoOrden.CANCELADA, models.EstadoOrden.DEVUELTA):
                prev = o.estado
                o.estado = models.EstadoOrden.CANCELADA
                o.save(update_fields=['estado', 'actualizado_en'])
                u = o.revertir_stock()
                unidades += u
                models.HistorialEstado.objects.create(
                    orden=o, estado_anterior=prev, estado_nuevo=models.EstadoOrden.CANCELADA, usuario=request.user
                )
                n += 1
        self.message_user(request, f"{n} orden(es) canceladas. Se reincorporaron {unidades} unidad(es) al stock.")
    marcar_cancelada.short_description = "Marcar como CANCELADA (repone stock al inventario)"

    def marcar_devuelta(self, request, queryset):
        n = 0
        unidades = 0
        for o in queryset:
            if o.estado in (models.EstadoOrden.ENTREGADA, models.EstadoOrden.ENVIADA):
                prev = o.estado
                o.estado = models.EstadoOrden.DEVUELTA
                o.save(update_fields=['estado', 'actualizado_en'])
                u = o.revertir_stock()
                unidades += u
                models.HistorialEstado.objects.create(
                    orden=o, estado_anterior=prev, estado_nuevo=models.EstadoOrden.DEVUELTA, usuario=request.user
                )
                n += 1
        self.message_user(request, f"{n} orden(es) marcadas como DEVUELTA. Se reincorporaron {unidades} unidad(es) al stock.")
    marcar_devuelta.short_description = "Marcar como DEVUELTA (repone stock al inventario)"


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
        list_display = ('id', 'orden', 'cliente', 'estado', 'resolucion', 'stock_revertido', 'creado_en')
        list_filter = ('estado', 'resolucion', 'stock_revertido')
        search_fields = ('orden__codigo', 'cliente__email')
        readonly_fields = ('creado_en', 'stock_revertido')


if hasattr(models, 'PoliticaGarantia'):
    @admin.register(models.PoliticaGarantia)
    class PoliticaGarantiaAdmin(admin.ModelAdmin):
        list_display = ('nombre', 'base', 'plazo_label', 'activa', 'orden_prioridad')
        list_filter = ('base', 'activa')
        list_editable = ('activa', 'orden_prioridad')
        search_fields = ('nombre', 'codigo')