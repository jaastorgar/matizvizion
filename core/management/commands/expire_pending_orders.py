"""
Cancela ordenes PENDIENTE expiradas (reservas sin pago) y devuelve su stock.
Uso:
    python manage.py expire_pending_orders              # cancela las de > 30 min
    python manage.py expire_pending_orders --minutes 15
    python manage.py expire_pending_orders --dry-run    # solo lista, no toca nada
Programar cada 10-15 min en produccion (cron / Task Scheduler).
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from orders.models import Orden


class Command(BaseCommand):
    help = 'Cancela ordenes PENDIENTE expiradas (sin pago) y repone su stock.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=30,
                            help='Minutos sin pago para considerar expirada (default 30).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo lista las ordenes expiradas, no cancela.')

    def handle(self, *args, **options):
        minutes = options['minutes']
        dry = options['dry_run']
        corte = timezone.now() - timedelta(minutes=minutes)
        pendientes = Orden.objects.filter(estado=Orden.Estado.PENDIENTE, creado_en__lte=corte)
        total = pendientes.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay ordenes PENDIENTE expiradas.'))
            return
        self.stdout.write(f'Ordenes PENDIENTE expiradas (>{minutes} min): {total}')
        canceladas = 0
        for orden in pendientes:
            if dry:
                self.stdout.write(f'  [dry-run] {orden.codigo} (creada {orden.creado_en:%Y-%m-%d %H:%M})')
                continue
            try:
                with transaction.atomic():
                    o = Orden.objects.select_for_update().get(pk=orden.pk)
                    if o.estado != Orden.Estado.PENDIENTE:
                        continue  # otra proceso ya la resolvio
                    o.revertir_stock()                       # el stock vuelve al inventario
                    o.cambiar_estado(Orden.Estado.CANCELADA, usuario=None)
                    try:
                        from core.notifications import notify_orden
                        notify_orden(o, Orden.Estado.CANCELADA)
                    except Exception:
                        pass
                    canceladas += 1
                    self.stdout.write(self.style.WARNING(f'  Cancelada {o.codigo} y stock repuesto.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error en {orden.codigo}: {e}'))
        if not dry:
            self.stdout.write(self.style.SUCCESS(f'Limpieza completada: {canceladas} orden(es) canceladas.'))