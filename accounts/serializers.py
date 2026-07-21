import re

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import CustomUser, PerfilCliente


RUT_REGEX = r'^\d{1,8}[0-9Kk]$'
TELEFONO_REGEX = r'^\+?\d{8,15}$'


def normalizar_rut(value):
    """
    Normaliza el RUT:
    - Quita puntos
    - Quita guion
    - Quita espacios
    - Convierte a mayúsculas
    Ejemplo:
        '12.345.678-5' -> '123456785'
    """
    return value.strip().upper().replace('.', '').replace('-', '').replace(' ', '')


def rut_tiene_dv_valido(rut):
    """
    Valida el dígito verificador del RUT chileno.
    """
    rut = normalizar_rut(rut)

    if not re.match(RUT_REGEX, rut):
        return False

    cuerpo = rut[:-1]
    dv = rut[-1].upper()

    suma = 0
    multiplicador = 2

    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = 11 - (suma % 11)

    if resto == 11:
        dv_esperado = '0'
    elif resto == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(resto)

    return dv == dv_esperado


def normalizar_telefono(value):
    """
    Normaliza el teléfono:
    - Quita espacios, guiones y paréntesis
    - Acepta formato internacional con +
    - Devuelve None si viene vacío
    """
    if value is None:
        return None

    telefono = re.sub(r'[^+\d]', '', value)

    if telefono == '':
        return None

    if not re.match(TELEFONO_REGEX, telefono):
        raise serializers.ValidationError(
            'El teléfono debe tener entre 8 y 15 dígitos. Ejemplo: +56912345678.'
        )

    return telefono


def normalizar_texto_opcional(value):
    """
    Convierte strings vacíos a None.
    """
    if value is None:
        return None

    value = value.strip()
    return value if value else None


class RegistroClienteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    role = serializers.CharField(read_only=True)

    rut = serializers.CharField(
        max_length=12,
        write_only=True
    )
    telefono = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        write_only=True
    )
    direccion = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'password',
            'first_name',
            'last_name',
            'role',
            'rut',
            'telefono',
            'direccion',
        ]
        extra_kwargs = {
            'password': {
                'write_only': True,
                'style': {'input_type': 'password'}
            },
            'first_name': {
                'required': False,
                'allow_blank': True
            },
            'last_name': {
                'required': False,
                'allow_blank': True
            },
        }

    def validate_email(self, value):
        email = value.strip().lower()

        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Este correo ya está registrado.')

        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_rut(self, value):
        rut = normalizar_rut(value)

        if not re.match(RUT_REGEX, rut):
            raise serializers.ValidationError(
                'Formato de RUT inválido. Usa un formato como 12345678-9.'
            )

        if not rut_tiene_dv_valido(rut):
            raise serializers.ValidationError(
                'El dígito verificador del RUT es inválido.'
            )

        if PerfilCliente.objects.filter(rut=rut).exists():
            raise serializers.ValidationError('Este RUT ya está registrado.')

        return rut

    def validate_telefono(self, value):
        return normalizar_telefono(value)

    def validate_direccion(self, value):
        return normalizar_texto_opcional(value)

    @transaction.atomic
    def create(self, validated_data):
        rut = validated_data.pop('rut')
        telefono = validated_data.pop('telefono', None)
        direccion = validated_data.pop('direccion', None)

        user = CustomUser.objects.create_user(
            email=validated_data.get('email'),
            password=validated_data.get('password'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='CLIENTE'
        )

        PerfilCliente.objects.create(
            user=user,
            rut=rut,
            telefono=telefono,
            direccion=direccion
        )

        return user


class PerfilClienteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source='user.email',
        read_only=True
    )
    first_name = serializers.CharField(
        source='user.first_name',
        required=False,
        allow_blank=True,
        max_length=150
    )
    last_name = serializers.CharField(
        source='user.last_name',
        required=False,
        allow_blank=True,
        max_length=150
    )
    telefono = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=15
    )
    direccion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    class Meta:
        model = PerfilCliente
        fields = [
            'email',
            'first_name',
            'last_name',
            'rut',
            'telefono',
            'direccion',
        ]
        read_only_fields = ['rut']

    def validate_telefono(self, value):
        return normalizar_telefono(value)

    def validate_direccion(self, value):
        return normalizar_texto_opcional(value)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        if user_data:
            user = instance.user
            update_fields = []

            if 'first_name' in user_data:
                user.first_name = user_data['first_name']
                update_fields.append('first_name')

            if 'last_name' in user_data:
                user.last_name = user_data['last_name']
                update_fields.append('last_name')

            if update_fields:
                user.save(update_fields=update_fields)

        instance.telefono = validated_data.get('telefono', instance.telefono)
        instance.direccion = validated_data.get('direccion', instance.direccion)
        instance.save()

        return instance