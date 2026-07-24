from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    Manager personalizado para el modelo CustomUser.
    Usa email como campo de autenticacion en lugar de username.
    """
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email).strip().lower()
        extra_fields.setdefault('role', 'CLIENTE')
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_guest(self, email, **extra_fields):
        """
        Crea un usuario INVITADO: sin contraseña utilizable y con is_guest=True.
        No crea PerfilCliente (el RUT es obligatorio y se pedira mas tarde).
        """
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email).strip().lower()
        extra_fields.setdefault('role', 'CLIENTE')
        extra_fields.setdefault('is_active', True)
        extra_fields['is_guest'] = True
        user = self.model(email=email, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        if extra_fields.get('role') != 'ADMIN':
            extra_fields['role'] = 'ADMIN'
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Usuario personalizado del sistema.
    Usa email como identificador unico y agrega rol para RBAC.
    """
    class Role(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        VENDEDOR = 'VENDEDOR', 'Vendedor'
        ADMIN = 'ADMIN', 'Administrador'

    username = None
    email = models.EmailField('Correo electrónico', unique=True)
    role = models.CharField(
        'Rol de usuario', max_length=10, choices=Role.choices,
        default=Role.CLIENTE, db_index=True
    )
    is_guest = models.BooleanField(
        'Cuenta invitada (sin contraseña)', default=False, db_index=True,
        help_text='True para compradores invitados creados sin contraseña.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=['CLIENTE', 'VENDEDOR', 'ADMIN']),
                name='accounts_user_role_valid'
            )
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class PerfilCliente(models.Model):
    """
    Perfil adicional para usuarios con rol CLIENTE.
    """
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='perfil_cliente'
    )
    rut = models.CharField('RUT', max_length=12, unique=True)
    telefono = models.CharField('Teléfono', max_length=15, blank=True, null=True)
    direccion = models.TextField('Dirección de despacho', blank=True, null=True)

    class Meta:
        verbose_name = 'Perfil cliente'
        verbose_name_plural = 'Perfiles cliente'
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(rut=''), name='perfil_cliente_rut_not_empty'
            )
        ]

    @staticmethod
    def normalizar_rut(rut):
        if not rut:
            return rut
        return rut.strip().upper().replace('.', '').replace('-', '').replace(' ', '')

    def clean(self):
        super().clean()
        self.rut = self.normalizar_rut(self.rut)

    def save(self, *args, **kwargs):
        self.rut = self.normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Perfil Cliente: {self.user.email} - RUT: {self.rut}"


class PerfilVendedor(models.Model):
    """
    Perfil adicional para usuarios con rol VENDEDOR.
    """
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='perfil_vendedor'
    )
    sucursal = models.ForeignKey(
        'core.Sucursal', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vendedores'
    )
    codigo_vendedor = models.CharField('Código vendedor', max_length=20, unique=True)

    class Meta:
        verbose_name = 'Perfil vendedor'
        verbose_name_plural = 'Perfiles vendedor'
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(codigo_vendedor=''),
                name='perfil_vend_codigo_not_empty'
            )
        ]

    def clean(self):
        super().clean()
        if self.codigo_vendedor:
            self.codigo_vendedor = self.codigo_vendedor.strip().upper()

    def save(self, *args, **kwargs):
        if self.codigo_vendedor:
            self.codigo_vendedor = self.codigo_vendedor.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        sucursal_nombre = (
            getattr(self.sucursal, 'nombre', 'Sin Sucursal')
            if self.sucursal else 'Sin Sucursal'
        )
        return (
            f"Perfil Vendedor: {self.user.email} "
            f"[{self.codigo_vendedor}] - {sucursal_nombre}"
        )