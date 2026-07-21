from django.contrib import admin

from .models import Sucursal


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'direccion',
        'telefono',
        'activa',
    )
    search_fields = (
        'nombre',
        'direccion',
        'telefono',
    )
    list_filter = (
        'activa',
    )
    ordering = (
        'nombre',
    )