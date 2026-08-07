from django.contrib import admin
from . import models


@admin.register(models.Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)