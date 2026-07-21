from rest_framework import serializers

from .models import Categoria, Producto, RecetaOptica


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'slug', 'descripcion']
        read_only_fields = fields


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source='categoria.nombre',
        read_only=True
    )
    en_stock = serializers.BooleanField(read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre',
            'descripcion',
            'precio',
            'stock',
            'en_stock',
            'imagen',
            'imagen_url',
            'categoria',
            'categoria_nombre',
            'destacado',
        ]
        read_only_fields = fields

    def get_imagen_url(self, obj):
        if not obj.imagen:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.imagen.url)
        return obj.imagen.url


class RecetaOpticaSerializer(serializers.ModelSerializer):
    cliente_email = serializers.EmailField(
        source='cliente.user.email',
        read_only=True
    )

    class Meta:
        model = RecetaOptica
        fields = [
            'id',
            'cliente',
            'cliente_email',
            'esfera_od',
            'esfera_oi',
            'cilindro_od',
            'cilindro_oi',
            'eje_od',
            'eje_oi',
            'add_od',
            'add_oi',
            'observaciones',
            'creado_en',
        ]
        read_only_fields = ['id', 'cliente', 'cliente_email', 'creado_en']