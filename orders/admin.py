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