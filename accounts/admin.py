from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models


@admin.register(models.CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('last_login', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name')}),
        ('Rol y permisos', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'role', 'is_staff', 'is_superuser')}),
    )


@admin.register(models.PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'telefono', 'comuna', 'region')
    search_fields = ('user__email', 'rut')


@admin.register(models.PerfilVendedor)
class PerfilVendedorAdmin(admin.ModelAdmin):
    list_display = ('user', 'codigo_vendedor', 'sucursal')
    search_fields = ('user__email', 'codigo_vendedor')
    list_filter = ('sucursal',)