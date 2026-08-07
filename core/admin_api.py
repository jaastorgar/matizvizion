import base64

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from accounts.models import CustomUser, PerfilCliente
from accounts.permissions import IsAdminUserCustom
from accounts.serializers import normalizar_rut, rut_tiene_dv_valido
from appointments.models import BloqueHorario, Tecnologo
from core.models import Sucursal
from store.models import Categoria, Producto


class AdminMixin:
    permission_classes = [IsAdminUserCustom]


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class ProductoSerializer(serializers.ModelSerializer):
    # La imagen entra como data-URL base64 (write_only) y sale como URL publica.
    imagen = serializers.CharField(required=False, allow_blank=True, write_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'sku', 'nombre', 'descripcion', 'precio', 'stock', 'stock_minimo',
                  'activo', 'destacado', 'categoria', 'imagen', 'imagen_url',
                  'creado_en', 'actualizado_en']
        read_only_fields = ['id', 'sku', 'creado_en', 'actualizado_en']

    def get_imagen_url(self, obj):
        if not obj.imagen:
            return None
        try:
            return obj.imagen.url
        except Exception:
            return None


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'


class TecnologoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tecnologo
        fields = '__all__'


class BloqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloqueHorario
        fields = '__all__'


class UsuarioSerializer(serializers.ModelSerializer):
    rut = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    direccion = serializers.SerializerMethodField()
    comuna = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_superuser',
                  'rut', 'telefono', 'direccion', 'comuna', 'region']

    def _perfil(self, o):
        return getattr(o, 'perfil_cliente', None)

    def get_rut(self, o):
        p = self._perfil(o)
        return p.rut if p else ''

    def get_telefono(self, o):
        p = self._perfil(o)
        return (p.telefono or '') if p else ''

    def get_direccion(self, o):
        p = self._perfil(o)
        return (p.direccion or '') if p else ''

    def get_comuna(self, o):
        p = self._perfil(o)
        return (p.comuna or '') if p else ''

    def get_region(self, o):
        p = self._perfil(o)
        return (p.region or '') if p else ''


class CategoriaViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class ProductoViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = Producto.objects.select_related('categoria').all()
    serializer_class = ProductoSerializer

    def _aplicar_imagen(self, producto, data_url):
        """Decodifica un data-URL base64 y lo guarda en media/productos/."""
        if not data_url or ',' not in data_url:
            return
        try:
            header, data = data_url.split(',', 1)
            ext = header.split('/')[1].split(';')[0].lower()
            if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
                ext = 'jpg'
            nombre = slugify(producto.nombre) or 'producto'
            producto.imagen.save(
                f"{nombre}_{producto.pk}.{ext}",
                ContentFile(base64.b64decode(data)),
                save=True,
            )
        except Exception:
            pass

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        imagen_b64 = ser.validated_data.pop('imagen', None) or None
        producto = ser.save()
        if imagen_b64:
            self._aplicar_imagen(producto, imagen_b64)
        return Response(self.get_serializer(producto).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        imagen_b64 = ser.validated_data.pop('imagen', None) or None
        instance = ser.save()
        if imagen_b64:
            self._aplicar_imagen(instance, imagen_b64)
        return Response(self.get_serializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class SucursalViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer


class TecnologoViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = Tecnologo.objects.select_related('sucursal').all()
    serializer_class = TecnologoSerializer


class BloqueViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = BloqueHorario.objects.select_related('tecnologo').all()
    serializer_class = BloqueSerializer


class UsuarioViewSet(AdminMixin, viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UsuarioSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({'error': 'No puedes eliminar tu propio usuario.'}, status=status.HTTP_400_BAD_REQUEST)
        from appointments.models import CitaMedica
        for c in CitaMedica.objects.filter(cliente=user, estado__in=['AGENDADA', 'CONFIRMADA']).select_related('bloque'):
            c.bloque.disponible = True
            c.bloque.save(update_fields=['disponible'])
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''
        role = request.data.get('role') or 'CLIENTE'
        if not email or '@' not in email:
            return Response({'error': 'Correo invalido.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({'error': 'La contrasena debe tener al menos 8 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        if role not in ['CLIENTE', 'VENDEDOR', 'ADMIN']:
            return Response({'error': 'Rol invalido.'}, status=status.HTTP_400_BAD_REQUEST)
        if CustomUser.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Ya existe un usuario con ese correo.'}, status=status.HTTP_400_BAD_REQUEST)

        rut = None
        rut_raw = (request.data.get('rut') or '').strip()
        if role == 'CLIENTE' and rut_raw:
            rut = normalizar_rut(rut_raw)
            if not rut_tiene_dv_valido(rut):
                return Response({'error': 'RUT invalido.'}, status=status.HTTP_400_BAD_REQUEST)
            if PerfilCliente.objects.filter(rut=rut).exists():
                return Response({'error': 'Ya existe un cliente con ese RUT.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = CustomUser(
                email=email,
                role=role,
                first_name=request.data.get('first_name') or '',
                last_name=request.data.get('last_name') or '',
                is_active=bool(request.data.get('is_active', True)),
                is_staff=(role == 'ADMIN'),
            )
            user.set_password(password)
            user.save()
            if rut:
                PerfilCliente.objects.create(
                    user=user,
                    rut=rut,
                    telefono=(request.data.get('telefono') or None),
                    direccion=(request.data.get('direccion') or None),
                    comuna=(request.data.get('comuna') or ''),
                    region=(request.data.get('region') or ''),
                )
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        for f in ['first_name', 'last_name', 'role', 'is_active']:
            if f in request.data:
                setattr(user, f, request.data[f])
        if 'role' in request.data:
            user.is_staff = (user.role == 'ADMIN')
        pw = request.data.get('password') or ''
        if pw:
            if len(pw) < 8:
                return Response({'error': 'La contrasena debe tener al menos 8 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(pw)
        user.save()

        if user.role == 'CLIENTE':
            perfil = getattr(user, 'perfil_cliente', None)
            rut_raw = (request.data.get('rut') or '').strip()
            if perfil is None and rut_raw:
                rut = normalizar_rut(rut_raw)
                if rut_tiene_dv_valido(rut) and not PerfilCliente.objects.filter(rut=rut).exists():
                    perfil = PerfilCliente.objects.create(user=user, rut=rut)
            if perfil is not None:
                if rut_raw:
                    rut = normalizar_rut(rut_raw)
                    if rut_tiene_dv_valido(rut) and not PerfilCliente.objects.filter(rut=rut).exclude(pk=perfil.pk).exists():
                        perfil.rut = rut
                for f in ['telefono', 'direccion']:
                    if f in request.data:
                        setattr(perfil, f, request.data[f] or None)
                for f in ['comuna', 'region']:
                    if f in request.data:
                        setattr(perfil, f, request.data[f] or '')
                perfil.save()
        return Response(self.get_serializer(user).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


admin_router = DefaultRouter()
admin_router.register('categorias', CategoriaViewSet, basename='admin-categorias')
admin_router.register('productos', ProductoViewSet, basename='admin-productos')
admin_router.register('sucursales', SucursalViewSet, basename='admin-sucursales')
admin_router.register('tecnologos', TecnologoViewSet, basename='admin-tecnologos')
admin_router.register('bloques', BloqueViewSet, basename='admin-bloques')
admin_router.register('usuarios', UsuarioViewSet, basename='admin-usuarios')