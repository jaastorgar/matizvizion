from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Categoria(models.Model):
    """
    Categoría de catálogo (p. ej. Armazones, Lentes de Sol, Contacto).
    """
    nombre = models.CharField('Nombre de categoría', max_length=100)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)
    descripcion = models.TextField('Descripción', blank=True, null=True)
    orden = models.PositiveIntegerField('Orden de aparición', default=0)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        # Autogenera el slug desde el nombre si viene vacío
        if not self.slug and self.nombre:
            base_slug = slugify(self.nombre) or 'categoria'
            slug = base_slug
            contador = 1
            while Categoria.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{contador}"
                contador += 1
            self.slug = slug

        if self.nombre:
            self.nombre = self.nombre.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """
    Producto del catálogo (armazones, lentes, accesorios).
    """
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='productos'
    )
    nombre = models.CharField('Nombre del producto', max_length=150)
    descripcion = models.TextField('Descripción', blank=True, null=True)
    precio = models.DecimalField(
        'Precio público',
        max_digits=10,
        decimal_places=2
    )
    stock = models.IntegerField('Stock disponible', default=0)
    imagen = models.ImageField(
        'Imagen del producto',
        upload_to='productos/',
        blank=True,
        null=True
    )
    activo = models.BooleanField(
        'Visible en catálogo',
        default=True,
        db_index=True,
        help_text='Si se desmarca, el producto no aparece en la tienda pública.'
    )
    destacado = models.BooleanField(
        'Destacado en home',
        default=False,
        db_index=True
    )
    creado_en = models.DateTimeField('Creado', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name='stock_no_negativo'
            ),
            models.CheckConstraint(
                condition=models.Q(precio__gte=0),
                name='precio_no_negativo'
            ),
        ]

    @property
    def en_stock(self):
        return self.stock > 0

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class RecetaOptica(models.Model):
    """
    Receta óptica asociada al perfil de un cliente.
    """
    cliente = models.ForeignKey(
        'accounts.PerfilCliente',
        on_delete=models.CASCADE,
        related_name='recetas'
    )
    esfera_od = models.DecimalField(
        'Esfera ojo derecho (OD)', max_digits=4, decimal_places=2
    )
    esfera_oi = models.DecimalField(
        'Esfera ojo izquierdo (OI)', max_digits=4, decimal_places=2
    )
    cilindro_od = models.DecimalField(
        'Cilindro OD', max_digits=4, decimal_places=2, blank=True, null=True
    )
    cilindro_oi = models.DecimalField(
        'Cilindro OI', max_digits=4, decimal_places=2, blank=True, null=True
    )
    eje_od = models.IntegerField('Eje OD (0-180)', blank=True, null=True)
    eje_oi = models.IntegerField('Eje OI (0-180)', blank=True, null=True)
    add_od = models.DecimalField(
        'Adición OD', max_digits=3, decimal_places=2, blank=True, null=True
    )
    add_oi = models.DecimalField(
        'Adición OI', max_digits=3, decimal_places=2, blank=True, null=True
    )
    observaciones = models.TextField('Observaciones', blank=True, null=True)
    creado_en = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Receta óptica'
        verbose_name_plural = 'Recetas ópticas'
        ordering = ['-creado_en']

    def clean(self):
        super().clean()

        # Rangos clínicos razonables
        for valor, etiqueta in (
            (self.esfera_od, 'Esfera OD'),
            (self.esfera_oi, 'Esfera OI'),
        ):
            if valor is not None and not (-25 <= valor <= 25):
                raise ValidationError(f'{etiqueta} fuera de rango (-25 a 25).')

        for valor, etiqueta in (
            (self.eje_od, 'Eje OD'),
            (self.eje_oi, 'Eje OI'),
        ):
            if valor is not None and not (0 <= valor <= 180):
                raise ValidationError(f'{etiqueta} debe estar entre 0 y 180.')

        # Si hay cilindro, debería haber eje (regla clínica habitual)
        if self.cilindro_od not in (None, 0) and self.eje_od is None:
            raise ValidationError('Si indicas Cilindro OD, debes indicar Eje OD.')
        if self.cilindro_oi not in (None, 0) and self.eje_oi is None:
            raise ValidationError('Si indicas Cilindro OI, debes indicar Eje OI.')

    def __str__(self):
        return f"Receta de {self.cliente.user.email} ({self.creado_en:%Y-%m-%d})"