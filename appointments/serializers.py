from rest_framework import serializers
from .models import Tecnologo, BloqueHorario, CitaMedica

class TecnologoSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.ReadOnlyField(source='sucursal.nombre')
    class Meta:
        model = Tecnologo
        fields = ['id', 'nombre', 'especialidad', 'sucursal', 'sucursal_nombre']

class BloqueHorarioSerializer(serializers.ModelSerializer):
    tecnologo_nombre = serializers.ReadOnlyField(source='tecnologo.nombre')
    class Meta:
        model = BloqueHorario
        fields = ['id', 'tecnologo', 'tecnologo_nombre', 'fecha', 'hora_inicio', 'hora_fin', 'disponible']

class CitaMedicaSerializer(serializers.ModelSerializer):
    cliente_email = serializers.ReadOnlyField(source='cliente.email')
    bloque_fecha = serializers.ReadOnlyField(source='bloque.fecha')
    bloque_hora_inicio = serializers.ReadOnlyField(source='bloque.hora_inicio')
    bloque_hora_fin = serializers.ReadOnlyField(source='bloque.hora_fin')
    tecnologo_nombre = serializers.ReadOnlyField(source='bloque.tecnologo.nombre')
    sucursal_nombre = serializers.ReadOnlyField(source='bloque.tecnologo.sucursal.nombre')
    class Meta:
        model = CitaMedica
        fields = ['id', 'cliente', 'cliente_email', 'bloque', 'bloque_fecha', 'bloque_hora_inicio',
                  'bloque_hora_fin', 'tecnologo_nombre', 'sucursal_nombre', 'estado', 'fecha_reserva']
        read_only_fields = ['id', 'cliente', 'cliente_email', 'bloque_fecha', 'bloque_hora_inicio',
                            'bloque_hora_fin', 'tecnologo_nombre', 'sucursal_nombre', 'estado', 'fecha_reserva']