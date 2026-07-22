from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from orders.models import HistorialEstado, Orden
from store.models import Producto

class Command(BaseCommand):
    help = 'Cancela ordenes PENDIENTE expiradas (reservas no pagadas) y libera el stock reservado.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=30,
                            help='Minutos de antiguedad para considerar la reserva expirada (0 = todas las PENDIENTE).')

    def handle(self, *args, **options):
        minutes = options['minutes']
        corte = timezone.now() - timedelta(minutes=minutes)
        pendientes = list(
            Orden.objects.filter(estado='PENDIENTE', creado_en__lte=corte)
            .select_related('cliente')
            .order_by('creado_en')
        )
        if not pendientes:
            self.stdout.write(self.style.WARNING('No hay ordenes PENDIENTE expiradas para limpiar.'))
            return

        canceladas = 0
        for orden in pendientes:
            try:
                with transaction.atomic():
                    o = Orden.objects.select_for_update().get(pk=orden.pk)
                    if o.estado != 'PENDIENTE':
                        continue  # otra proceso ya la resolvio
                    # 1) Liberar el stock reservado (bloqueo de fila por producto)
                    liberado = 0
                    for it in o.items.select_related('producto').all():
                        p = Producto.objects.select_for_update().get(pk=it.producto_id)
                        p.stock = F('stock') + it.cantidad
                        p.save(update_fields=['stock'])
                        liberado += it.cantidad
                    # 2) Cancelar la orden y dejar trazabilidad (inmune a la version del modelo)
                    o.estado = 'CANCELADA'
                    o.save(update_fields=['estado'])
                    HistorialEstado.objects.create(
                        orden=o, estado_anterior='PENDIENTE', estado_nuevo='CANCELADA'
                    )
                    canceladas += 1
                    self.stdout.write(f'  - Orden #{o.id} cancelada (stock liberado: {liberado} u.)')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ! Error en orden #{orden.id}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Expiracion completada: {canceladas} orden(es) PENDIENTE canceladas y su stock liberado.'
        ))
        self.stdout.write(self.style.WARNING(
            'Nota (solo desarrollo): si antes corriste seed_demo (que fija el stock a valores oficiales), '
            'vuelve a correrlo una vez para dejar el stock canonicamente en sus valores de catalogo.'
        ))