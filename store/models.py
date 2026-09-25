import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Categoria(models.Model):
    nombre = models.CharField('Nombre de categoria', max_length=100)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)
    descripcion = models.TextField('Descripcion', blank=True, null=True)
    orden = models.PositiveIntegerField('Orden de aparicion', default=0)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.slug and self.nombre:
            base = slugify(self.nombre) or 'categoria'
            slug = base
            n = 1
            while Categoria.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField('Nombre del producto', max_length=150)
    descripcion = models.TextField('Descripcion', blank=True, null=True)
    sku = models.CharField(
        'SKU / Codigo unico', max_length=40, unique=True, null=True, blank=True,
        help_text='Codigo unico de catalogo. Se autogenera si se deja vacio.'
    )
    precio = models.DecimalField('Precio publico', max_digits=10, decimal_places=2)
    stock = models.IntegerField('Stock disponible', default=0)
    stock_minimo = models.IntegerField(
        'Stock minimo (alerta)', default=5,
        help_text='Cuando el stock cae a este valor o menos, se dispara una alerta.'
    )
    imagen = models.ImageField('Imagen del producto', upload_to='productos/', blank=True, null=True)
    imagen_tryon = models.ImageField(
        'Imagen PNG frontal transparente (Probador virtual)',
        upload_to='productos/tryon/', blank=True, null=True,
        help_text='PNG frontal con fondo transparente para superponer en el rostro en el probador virtual.'
    )
    activo = models.BooleanField('Visible en catalogo', default=True, db_index=True)
    destacado = models.BooleanField('Destacado en home', default=False, db_index=True)
    grupo = models.CharField('Grupo/Familia (colores)', max_length=60, blank=True, default='', db_index=True,
        help_text='Productos con el mismo grupo se muestran como una sola tarjeta con selector de color.')
    color = models.CharField('Color (etiqueta)', max_length=60, blank=True, default='')
    configurable_lente = models.BooleanField('Configurable como lente (tipo y distancia)', default=False, help_text='Si se activa, el catalogo ofrece elegir diseno focal y distancia de uso.')
    creado_en = models.DateTimeField('Creado', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(condition=models.Q(stock__gte=0), name='stock_no_negativo'),
            models.CheckConstraint(condition=models.Q(precio__gte=0), name='precio_no_negativo'),
        ]

    @property
    def en_stock(self):
        return self.stock > 0

    @property
    def stock_bajo(self):
        umbral = self.stock_minimo if self.stock_minimo is not None else getattr(settings, 'STOCK_ALERT_THRESHOLD', 5)
        return self.stock <= umbral

    def _generar_sku(self):
        base = self.categoria.nombre if self.categoria_id else 'PRD'
        pref = re.sub(r'[^A-Z0-9]', '', base.upper())[:4] or 'PRD'
        return f"{pref}-{self.pk:04d}"

    def save(self, *args, **kwargs):
        # Captura el stock previo para detectar cruce de umbral hacia abajo
        prev_stock = None
        prev_imagen = None
        if self.pk:
            prev_stock = Producto.objects.filter(pk=self.pk).values_list('stock', flat=True).first()
            prev_imagen = Producto.objects.filter(pk=self.pk).values_list('imagen', flat=True).first()
        if self.nombre:
            self.nombre = self.nombre.strip()
        super().save(*args, **kwargs)
        if not self.sku:
            self.sku = self._generar_sku()
            super().save(update_fields=['sku'])
        # Si la imagen fue reemplazada, elimina el archivo anterior del disco
        if prev_imagen and prev_imagen != self.imagen:
            try:
                from django.core.files.storage import default_storage
                if default_storage.exists(prev_imagen):
                    default_storage.delete(prev_imagen)
            except Exception:
                pass
        # Signal de alerta: solo si el stock CRUZO el umbral hacia abajo
        if prev_stock is not None:
            umbral = self.stock_minimo if self.stock_minimo is not None else getattr(settings, 'STOCK_ALERT_THRESHOLD', 5)
            if prev_stock > umbral and self.stock <= umbral:
                self._notificar_stock_bajo(umbral)

    def delete(self, *args, **kwargs):
        # Elimina tambien el archivo de imagen (media/productos/) al borrar el producto
        try:
            if self.imagen:
                self.imagen.delete(save=False)
        except Exception:
            pass
        return super().delete(*args, **kwargs)

    def _notificar_stock_bajo(self, umbral):
        """Manda mail a ADMIN/VENDEDOR cuando un producto cruza el umbral hacia abajo."""
        try:
            from django.core.mail import send_mail
            from accounts.models import CustomUser
            destinatarios = list(
                CustomUser.objects.filter(role__in=['ADMIN', 'VENDEDOR'], is_active=True)
                .values_list('email', flat=True)
            )
            if not destinatarios:
                return
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Matizvision <no-reply@matizvision.cl>')
            tag = 'AGOTADO' if self.stock <= 0 else 'STOCK BAJO'
            asunto = f'[Matizvision] {tag}: {self.nombre} (stock {self.stock})'
            cuerpo = (
                f'El producto "{self.nombre}" (SKU {self.sku or "-"}) cruzó el umbral de stock.\n'
                f'Stock actual: {self.stock}\n'
                f'Umbral: {umbral}\n\n'
                f'Reponer para no perder ventas.'
            )
            send_mail(asunto, cuerpo, from_email, destinatarios, fail_silently=True)
        except Exception:
            pass

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class RecetaOptica(models.Model):
    cliente = models.ForeignKey('accounts.PerfilCliente', on_delete=models.CASCADE, related_name='recetas')
    esfera_od = models.DecimalField('Esfera OD', max_digits=4, decimal_places=2)
    esfera_oi = models.DecimalField('Esfera OI', max_digits=4, decimal_places=2)
    cilindro_od = models.DecimalField('Cilindro OD', max_digits=4, decimal_places=2, blank=True, null=True)
    cilindro_oi = models.DecimalField('Cilindro OI', max_digits=4, decimal_places=2, blank=True, null=True)
    eje_od = models.IntegerField('Eje OD (0-180)', blank=True, null=True)
    eje_oi = models.IntegerField('Eje OI (0-180)', blank=True, null=True)
    add_od = models.DecimalField('Adicion OD', max_digits=3, decimal_places=2, blank=True, null=True)
    add_oi = models.DecimalField('Adicion OI', max_digits=3, decimal_places=2, blank=True, null=True)
    observaciones = models.TextField('Observaciones', blank=True, null=True)
    creado_en = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Receta optica'
        verbose_name_plural = 'Recetas opticas'
        ordering = ['-creado_en']

    def clean(self):
        super().clean()
        for v, e in ((self.esfera_od, 'Esfera OD'), (self.esfera_oi, 'Esfera OI')):
            if v is not None and not (-25 <= v <= 25):
                raise ValidationError(f'{e} fuera de rango (-25 a 25).')
        for v, e in ((self.eje_od, 'Eje OD'), (self.eje_oi, 'Eje OI')):
            if v is not None and not (0 <= v <= 180):
                raise ValidationError(f'{e} debe estar entre 0 y 180.')
        if self.cilindro_od not in (None, 0) and self.eje_od is None:
            raise ValidationError('Si indicas Cilindro OD, debes indicar Eje OD.')
        if self.cilindro_oi not in (None, 0) and self.eje_oi is None:
            raise ValidationError('Si indicas Cilindro OI, debes indicar Eje OI.')

    def __str__(self):
        return f"Receta de {self.cliente.user.email} ({self.creado_en:%Y-%m-%d})"
