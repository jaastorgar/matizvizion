import re
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from .models import CustomUser, PerfilCliente

RUT_REGEX = r'^\d{1,8}[0-9Kk]$'
TELEFONO_REGEX = r'^\+?\d{8,15}$'


def normalizar_rut(value):
    return value.strip().upper().replace('.', '').replace('-', '').replace(' ', '')


def rut_tiene_dv_valido(rut):
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
    if value is None:
        return None
    value = value.strip()
    return value if value else None


class RegistroClienteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    role = serializers.CharField(read_only=True)
    rut = serializers.CharField(max_length=12, write_only=True)
    telefono = serializers.CharField(max_length=15, write_only=True)
    direccion = serializers.CharField(write_only=True)
    comuna = serializers.CharField(max_length=80, write_only=True)
    region = serializers.CharField(max_length=80, write_only=True)
    acepta_terminos = serializers.BooleanField(write_only=True, required=True)
    consiente_salud = serializers.BooleanField(write_only=True, required=False, default=False)
    consiente_marketing = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'password', 'first_name', 'last_name', 'role',
            'rut', 'telefono', 'direccion', 'comuna', 'region',
            'acepta_terminos', 'consiente_salud', 'consiente_marketing',
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
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
            raise serializers.ValidationError('Formato de RUT inválido. Usa un formato como 12345678-9.')
        if not rut_tiene_dv_valido(rut):
            raise serializers.ValidationError('El dígito verificador del RUT es inválido.')
        if PerfilCliente.objects.filter(rut=rut).exists():
            raise serializers.ValidationError('Este RUT ya está registrado.')
        return rut

    def validate_telefono(self, value):
        return normalizar_telefono(value)

    def validate_direccion(self, value):
        value = normalizar_texto_opcional(value)
        if not value:
            raise serializers.ValidationError('La dirección es obligatoria.')
        return value

    def validate_comuna(self, value):
        value = normalizar_texto_opcional(value)
        if not value:
            raise serializers.ValidationError('La comuna es obligatoria.')
        return value

    def validate_region(self, value):
        value = normalizar_texto_opcional(value)
        if not value:
            raise serializers.ValidationError('La región es obligatoria.')
        return value

    def validate_acepta_terminos(self, value):
        if value is not True:
            raise serializers.ValidationError('Debes aceptar los términos y la política de privacidad para registrarte.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        acepta_terminos = validated_data.pop('acepta_terminos', False)
        consiente_salud = validated_data.pop('consiente_salud', False)
        consiente_marketing = validated_data.pop('consiente_marketing', False)
        rut = validated_data.pop('rut')
        telefono = validated_data.pop('telefono', None)
        direccion = validated_data.pop('direccion', None)
        comuna = validated_data.pop('comuna')
        region = validated_data.pop('region')
        user = CustomUser.objects.create_user(
            email=validated_data.get('email'),
            password=validated_data.get('password'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='CLIENTE'
        )
        from .consent import sellar_terminos, sellar_salud, actualizar_marketing
        request = self.context.get('request')
        if acepta_terminos:
            sellar_terminos(user, request=request)
        if consiente_salud:
            sellar_salud(user, request=request)
        if consiente_marketing:
            actualizar_marketing(user, True, request=request)
        user.save()
        PerfilCliente.objects.create(
            user=user, rut=rut, telefono=telefono,
            direccion=direccion, comuna=comuna, region=region
        )
        return user


class PerfilClienteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True, max_length=150)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=15)
    direccion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    comuna = serializers.CharField(required=False, allow_blank=True, max_length=80)
    region = serializers.CharField(required=False, allow_blank=True, max_length=80)

    class Meta:
        model = PerfilCliente
        fields = [
            'email', 'first_name', 'last_name', 'rut',
            'telefono', 'direccion', 'comuna', 'region',
        ]
        read_only_fields = ['rut']

    def validate_telefono(self, value):
        return normalizar_telefono(value)

    def validate_direccion(self, value):
        return normalizar_texto_opcional(value)

    def validate_comuna(self, value):
        return normalizar_texto_opcional(value)

    def validate_region(self, value):
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
        instance.comuna = validated_data.get('comuna', instance.comuna)
        instance.region = validated_data.get('region', instance.region)
        instance.save()
        return instance