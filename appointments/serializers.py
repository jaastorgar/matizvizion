from datetime import date

from rest_framework import serializers

from .models import BloqueHorario, CitaMedica, Tecnologo


class TecnologoSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(
        source='sucursal.nombre',
        read_only=True
    )

    class Meta:
        model = Tecnologo
        fields = [
            'id',
            'nombre',
            'especialidad',
            'sucursal',
            'sucursal_nombre',
        ]
        read_only_fields = fields


class BloqueHorarioSerializer(serializers.ModelSerializer):
    tecnologo_nombre = serializers.CharField(
        source='tecnologo.nombre',
        read_only=True
    )

    class Meta:
        model = BloqueHorario
        fields = [
            'id',
            'tecnologo',
            'tecnologo_nombre',
            'fecha',
            'hora_inicio',
            'hora_fin',
            'disponible',
        ]
        read_only_fields = fields


class CitaMedicaSerializer(serializers.ModelSerializer):
    # Datos del bloque anidados (solo lectura) para el frontend
    bloque_fecha = serializers.DateField(source='bloque.fecha', read_only=True)
    bloque_hora_inicio = serializers.TimeField(source='bloque.hora_inicio', read_only=True)
    bloque_hora_fin = serializers.TimeField(source='bloque.hora_fin', read_only=True)
    tecnologo_nombre = serializers.CharField(
        source='bloque.tecnologo.nombre',
        read_only=True
    )
    sucursal_nombre = serializers.CharField(
        source='bloque.tecnologo.sucursal.nombre',
        read_only=True
    )
    cliente_email = serializers.EmailField(source='cliente.email', read_only=True)

    class Meta:
        model = CitaMedica
        fields = [
            'id',
            'cliente',
            'cliente_email',
            'bloque',
            'bloque_fecha',
            'bloque_hora_inicio',
            'bloque_hora_fin',
            'tecnologo_nombre',
            'sucursal_nombre',
            'estado',
            'fecha_reserva',
        ]
        read_only_fields = [
            'id',
            'cliente',
            'cliente_email',
            'estado',
            'fecha_reserva',
            'bloque_fecha',
            'bloque_hora_inicio',
            'bloque_hora_fin',
            'tecnologo_nombre',
            'sucursal_nombre',
        ]

    def validate_bloque(self, bloque):
        """
        Chequeo preliminar: el bloque debe existir, estar disponible
        y ser de una fecha no pasada. La reserva definitiva con bloqueo
        de fila se hace en la vista con select_for_update().
        """
        if not bloque.disponible:
            raise serializers.ValidationError('El bloque seleccionado ya no está disponible.')

        if bloque.fecha < date.today():
            raise serializers.ValidationError('No se puede agendar en una fecha pasada.')

        return bloque