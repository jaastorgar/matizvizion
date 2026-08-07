from django.contrib import admin
from . import models


@admin.register(models.Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'orden')
    search_fields = ('nombre',)
    ordering = ('orden', 'nombre')


@admin.register(models.Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sku', 'categoria', 'precio', 'stock', 'stock_minimo', 'activo', 'destacado')
    list_editable = ('precio', 'stock', 'stock_minimo', 'activo', 'destacado')
    list_filter = ('categoria', 'activo', 'destacado')
    search_fields = ('nombre', 'sku')
    readonly_fields = ('sku', 'creado_en', 'actualizado_en')
    ordering = ('nombre',)


@admin.register(models.RecetaOptica)
class RecetaOpticaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'creado_en')
    search_fields = ('cliente__user__email',)
    readonly_fields = ('creado_en',)