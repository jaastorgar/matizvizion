from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser, PerfilCliente, PerfilVendedor


class CustomUserCreationForm(UserCreationForm):
    """
    Formulario personalizado para crear usuarios en el admin.
    Se usa email en lugar de username.
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'role')
        field_classes = {}


class CustomUserChangeForm(UserChangeForm):
    """
    Formulario personalizado para editar usuarios en el admin.
    """
    class Meta:
        model = CustomUser
        fields = (
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )
        field_classes = {}


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    ordering = ('email',)

    list_display = (
        'email',
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
    )

    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
    )

    search_fields = (
        'email',
        'first_name',
        'last_name',
    )

    readonly_fields = (
        'last_login',
        'date_joined',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'email',
                    'password',
                )
            }
        ),
        (
            'Información personal',
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'role',
                )
            }
        ),
        (
            'Permisos',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            }
        ),
        (
            'Fechas importantes',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'role',
                    'password1',
                    'password2',
                ),
            }
        ),
    )

    actions = [
        'activar_usuarios',
        'desactivar_usuarios',
    ]

    @admin.action(description='Activar usuarios seleccionados')
    def activar_usuarios(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Desactivar usuarios seleccionados')
    def desactivar_usuarios(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'rut',
        'telefono',
    )

    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'rut',
    )

    list_filter = (
        'user__role',
    )

    raw_id_fields = (
        'user',
    )

    list_select_related = (
        'user',
    )


@admin.register(PerfilVendedor)
class PerfilVendedorAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'codigo_vendedor',
        'sucursal',
    )

    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'codigo_vendedor',
        'sucursal__nombre',
    )

    list_filter = (
        'sucursal',
    )

    raw_id_fields = (
        'user',
        'sucursal',
    )

    list_select_related = (
        'user',
        'sucursal',
    )