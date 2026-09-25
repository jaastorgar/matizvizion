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


@admin.register(models.ConsentimientoLog)
class ConsentimientoLogAdmin(admin.ModelAdmin):
    list_display = ('creado_en', 'usuario', 'email_snapshot', 'tipo', 'accion', 'version', 'ip_address')
    list_filter = ('tipo', 'accion', 'version', 'creado_en')
    search_fields = ('usuario__email', 'email_snapshot', 'ip_address')
    readonly_fields = ('creado_en', 'usuario', 'email_snapshot', 'tipo', 'accion', 'version', 'ip_address', 'user_agent')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.SolicitudSupresion)
class SolicitudSupresionAdmin(admin.ModelAdmin):
    list_display = ('creado_en', 'email_original', 'rut_asociado', 'ip_address')
    search_fields = ('email_original', 'rut_asociado', 'ip_address')
    readonly_fields = (
        'creado_en', 'usuario', 'email_original', 'rut_asociado',
        'ip_address', 'user_agent', 'motivo', 'detalle_resguardo'
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False