"""
Reporte de stock bajo. Manda por mail (y siempre imprime en terminal) la lista de
productos con stock <= umbral a los usuarios ADMIN y VENDEDOR activos.
Uso:
    python manage.py report_stock_alerts              # umbral de settings (default 5)
    python manage.py report_stock_alerts --threshold 3
    python manage.py report_stock_alerts --dry-run    # solo imprime, no manda mail
Programar 1 vez al dia en produccion (cron / Task Scheduler).
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Reporta por mail los productos con stock bajo o agotados.'

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=int, default=None,
                            help='Umbral de stock bajo (default: settings.STOCK_ALERT_THRESHOLD).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo imprime el reporte, no envia mail.')

    def handle(self, *args, **options):
        from store.models import Producto
        from accounts.models import CustomUser

        umbral = options['threshold']
        if umbral is None:
            umbral = getattr(settings, 'STOCK_ALERT_THRESHOLD', 5)

        productos = list(
            Producto.objects.filter(activo=True, stock__lte=umbral)
            .order_by('stock', 'nombre')
            .values('nombre', 'sku', 'stock')
        )

        # Siempre imprimimos el resumen en terminal (util en desarrollo)
        self.stdout.write(self.style.NOTICE(f'Reporte de stock bajo (umbral <= {umbral}): {len(productos)} producto(s).'))
        for p in productos:
            tag = 'AGOTADO' if p['stock'] <= 0 else 'BAJO'
            self.stdout.write(f'  [{tag}] {p["nombre"]} ({p["sku"] or "-"}) -> stock {p["stock"]}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('dry-run: no se envio mail.'))
            return

        # Destinatarios: ADMIN y VENDEDOR activos
        destinatarios = list(
            CustomUser.objects.filter(role__in=['ADMIN', 'VENDEDOR'], is_active=True)
            .values_list('email', flat=True)
        )
        if not destinatarios:
            self.stdout.write(self.style.WARNING('No hay usuarios ADMIN/VENDEDOR activos a quienes enviar el reporte.'))
            return

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Matizvision <no-reply@matizvision.cl>')
        body = render_to_string('emails/stock_alert.txt', {'umbral': umbral, 'productos': productos})
        asunto = f'[Matizvision] Alerta de stock: {len(productos)} producto(s) bajo umbral'
        try:
            send_mail(asunto, body, from_email, destinatarios, fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Reporte enviado a {len(destinatarios)} destinatario(s).'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'No se pudo enviar el mail: {e}'))