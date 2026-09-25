from django.contrib import admin
from .models import Receta


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'tipo', 'estado', 'vigencia_hasta', 'creado_en')
    list_filter = ('tipo',)
    search_fields = ('cliente__email', 'cliente__first_name', 'cliente__last_name', 'nombre')
    readonly_fields = ('creado_en', 'actualizado_en', 'subido_por')
