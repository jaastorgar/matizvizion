from rest_framework import serializers

from .models import Sucursal


class SucursalSerializer(serializers.ModelSerializer):
    """
    Serializer público para mostrar sucursales.
    """
    class Meta:
        model = Sucursal
        fields = [
            'id',
            'nombre',
            'direccion',
            'telefono',
        ]
        read_only_fields = [
            'id',
            'nombre',
            'direccion',
            'telefono',
        ]