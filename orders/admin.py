from django.contrib import admin

from .models import (
    Carrito,
    HistorialEstado,
    ItemCarrito,
    ItemOrden,
    Orden,
)


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    readonly_fields = ('subtotal',)


@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'total',
        'creado_en',
        'actualizado_en',
    )
    search_fields = (
        'cliente__email',
    )
    readonly_fields = (
        'creado_en',
        'actualizado_en',
        'total',
    )
    inlines = [
        ItemCarritoInline,
    ]


class ItemOrdenInline(admin.TabularInline):
    model = ItemOrden
    extra = 0
    readonly_fields = (
        'producto',
        'precio_unitario',
        'cantidad',
        'subtotal',
    )


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = (
        'estado_anterior',
        'estado_nuevo',
        'cambiado_en',
        'usuario',
    )
    ordering = ('-cambiado_en',)


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'total',
        'estado',
        'creado_en',
        'actualizado_en',
    )
    list_filter = (
        'estado',
        'creado_en',
    )
    search_fields = (
        'cliente__email',
        'id',
    )
    readonly_fields = (
        'cliente',
        'total',
        'creado_en',
        'actualizado_en',
    )
    inlines = [
        ItemOrdenInline,
        HistorialEstadoInline,
    ]


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'orden',
        'estado_anterior',
        'estado_nuevo',
        'cambiado_en',
        'usuario',
    )
    list_filter = (
        'estado_nuevo',
        'cambiado_en',
    )
    search_fields = (
        'orden__id',
        'usuario__email',
    )
    readonly_fields = (
        'orden',
        'estado_anterior',
        'estado_nuevo',
        'cambiado_en',
        'usuario',
    )

# ---- Registro de Politicas de garantia (Matizvision) ----
from .models import PoliticaGarantia as _PolGar


@admin.register(_PolGar)
class PoliticaGarantiaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'base', 'plazo_label', 'activa', 'orden_prioridad')
    list_filter = ('base', 'activa')
    list_editable = ('activa', 'orden_prioridad')
    search_fields = ('nombre', 'codigo')
    fieldsets = (
        (None, {'fields': ('codigo', 'nombre', 'base', 'activa', 'orden_prioridad')}),
        ('Cobertura', {'fields': ('descripcion', 'exclusiones')}),
        ('Plazo', {'fields': ('plazo_label', 'plazo_dias_min', 'plazo_dias_max')}),
        ('Resoluciones que ofrece', {'fields': (
            'permite_devolucion', 'permite_cambio', 'permite_reparacion', 'permite_rehacer')}),
        ('Aplicabilidad (refinado en nivel Completo)', {'fields': ('solo_con_receta', 'categorias'),
                                                       'classes': ('collapse',)}),
    )
