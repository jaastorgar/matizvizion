from rest_framework.permissions import BasePermission

class IsClienteUser(BasePermission):
    """Permite el acceso únicamente a usuarios con rol CLIENTE."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'CLIENTE')

class IsVendedorUser(BasePermission):
    """Permite el acceso a usuarios con rol VENDEDOR o ADMIN."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['VENDEDOR', 'ADMIN'])

class IsAdminUserCustom(BasePermission):
    """Permite el acceso únicamente a Administradores o Superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.role == 'ADMIN' or request.user.is_superuser))