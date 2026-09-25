from rest_framework import serializers
from .models import Receta

MAX_MB = 10
EXT_OK = ('.pdf', '.jpg', '.jpeg', '.png', '.webp')


class RecetaSerializer(serializers.ModelSerializer):
    cliente_email = serializers.EmailField(source='cliente.email', read_only=True)
    cliente_nombre = serializers.SerializerMethodField()
    subido_por_nombre = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = Receta
        fields = ['id', 'cliente', 'cliente_email', 'cliente_nombre', 'tipo', 'tipo_display',
                  'archivo', 'archivo_url', 'nombre', 'detalle', 'vigencia_hasta', 'estado',
                  'estado_display', 'notas', 'subido_por', 'subido_por_nombre', 'creado_en', 'actualizado_en']
        read_only_fields = ['id', 'subido_por', 'creado_en', 'actualizado_en']
        extra_kwargs = {'archivo': {'required': False}}

    def get_cliente_nombre(self, obj):
        u = obj.cliente
        dn = ((getattr(u, 'first_name', '') or '') + ' ' + (getattr(u, 'last_name', '') or '')).strip()
        return dn or (u.email if u else '')

    def get_subido_por_nombre(self, obj):
        u = obj.subido_por
        if not u:
            return ''
        dn = ((getattr(u, 'first_name', '') or '') + ' ' + (getattr(u, 'last_name', '') or '')).strip()
        return dn or u.email

    def get_archivo_url(self, obj):
        req = self.context.get('request')
        try:
            url = obj.archivo.url
        except Exception:
            return ''
        return req.build_absolute_uri(url) if req else url

    def get_estado(self, obj):
        return obj.estado

    def get_estado_display(self, obj):
        try:
            return Receta.Estado(obj.estado).label
        except Exception:
            return str(obj.estado)

    def validate(self, attrs):
        if not self.instance and not attrs.get('archivo') and not self.initial_data.get('archivo_base64'):
            raise serializers.ValidationError({'archivo': 'Debes adjuntar el archivo de la receta.'})
        return attrs

    def validate_archivo(self, f):
        name = (f.name or '').lower()
        if not name.endswith(EXT_OK):
            raise serializers.ValidationError('Formato no permitido. Usa PDF, JPG, JPEG, PNG o WEBP.')
        if f.size > MAX_MB * 1024 * 1024:
            raise serializers.ValidationError('El archivo supera %d MB.' % MAX_MB)
        return f
