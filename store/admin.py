from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Categoria, Producto, RecetaOptica


class EnStockFilter(admin.SimpleListFilter):
    """
    Filtro lateral para ver solo productos con stock o solo agotados.
    No se puede filtrar por la propiedad `en_stock`, así que lo hacemos
    por el campo real `stock`.
    """
    title = 'stock'
    parameter_name = 'en_stock'

    def lookups(self, request, model_admin):
        return (
            ('si', 'En stock'),
            ('no', 'Agotado'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'si':
            return queryset.filter(stock__gt=0)
        if self.value() == 'no':
            return queryset.filter(stock=0)
        return queryset


class ProductoInline(admin.TabularInline):
    model = Producto
    extra = 0
    fields = ('nombre', 'precio', 'stock', 'activo', 'destacado')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'orden', 'cantidad_productos')
    search_fields = ('nombre', 'slug')
    prepopulated_fields = {'slug': ('nombre',)}
    ordering = ('orden', 'nombre')
    inlines = [ProductoInline]

    def cantidad_productos(self, obj):
        return obj.productos.count()
    cantidad_productos.short_description = 'Productos'


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'categoria',
        'precio',
        'stock',
        'en_stock',
        'activo',
        'destacado',
    )
    # OJO: aquí va la CLASE de filtro, no el string 'en_stock'
    list_filter = ('activo', 'destacado', 'categoria', EnStockFilter)
    search_fields = ('nombre', 'descripcion', 'categoria__nombre')
    list_editable = ('precio', 'stock', 'activo', 'destacado')
    list_select_related = ('categoria',)
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        (None, {
            'fields': ('nombre', 'categoria', 'descripcion', 'imagen')
        }),
        ('Comercial', {
            'fields': ('precio', 'stock', 'activo', 'destacado')
        }),
        ('Sistema', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

    def en_stock(self, obj):
        return obj.stock > 0
    en_stock.boolean = True
    en_stock.short_description = 'En stock'


@admin.register(RecetaOptica)
class RecetaOpticaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'esfera_od',
        'esfera_oi',
        'eje_od',
        'eje_oi',
        'creado_en',
    )
    list_filter = ('creado_en',)
    search_fields = ('cliente__user__email', 'observaciones')
    list_select_related = ('cliente__user',)
    readonly_fields = ('creado_en',)

    def save_model(self, request, obj, form, change):
        try:
            obj.full_clean()
        except ValidationError as error:
            messages.error(request, '; '.join(error.messages))
            return
        super().save_model(request, obj, form, change)