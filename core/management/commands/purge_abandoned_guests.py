"""
Purga de cuentas de invitados y carritos abandonados.
Principio de Limitación del Plazo de Conservación (Ley N° 21.719 / Principio de Minimización).

Elimina cuentas temporales de invitados (is_guest=True) creadas hace más de N días
que NO posean compras concretadas, recetas oftalmológicas ni citas médicas.

Uso:
    python manage.py purge_abandoned_guests              # elimina invitados inactivos > 60 días
    python manage.py purge_abandoned_guests --days 30
    python manage.py purge_abandoned_guests --dry-run    # solo simula y reporta
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from orders.models import Carrito, Orden


class Command(BaseCommand):
    help = 'Purga cuentas de invitados abandonadas y carritos huérfanos sin actividad según Ley 21.719.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=60,
            help='Días de inactividad para considerar la cuenta abandonada (default: 60 días).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Modo simulación: reporta qué cuentas y carritos se purgarían sin eliminarlos.'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry = options['dry_run']
        corte = timezone.now() - timedelta(days=days)

        self.stdout.write(self.style.NOTICE(
            f"=== Purga de Datos Abandonados (Ley 21.719) [Umbral: > {days} días ({corte:%Y-%m-%d})] ==="
        ))
        if dry:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN activo: no se aplicarán cambios a la base de datos."))

        candidatos_invitados = CustomUser.objects.filter(is_guest=True, date_joined__lte=corte)
        total_candidatos = candidatos_invitados.count()

        usuarios_a_purgar = []
        for u in candidatos_invitados:
            # 1. Compras: no purgar si tiene órdenes pagadas, en curso o entregadas
            tiene_compras_reales = u.ordenes.exclude(
                estado__in=[Orden.Estado.PENDIENTE, Orden.Estado.CANCELADA, Orden.Estado.FALLIDA]
            ).exists()
            if tiene_compras_reales:
                continue

            # 2. Citas médicas: resguardo de ficha clínica
            if u.citas.exists():
                continue

            # 3. Recetas digitales subidas
            if hasattr(u, 'recetas') and u.recetas.exists():
                continue

            # 4. Recetas ópticas en perfil
            if hasattr(u, 'perfil_cliente') and u.perfil_cliente.recetas.exists():
                continue

            # 5. Garantías / devoluciones
            if hasattr(u, 'solicitudes_devolucion') and u.solicitudes_devolucion.exists():
                continue

            usuarios_a_purgar.append(u)

        self.stdout.write(
            f"Invitados evaluados: {total_candidatos} | Elegibles para purga: {len(usuarios_a_purgar)}"
        )

        purgados_usuarios = 0
        with transaction.atomic():
            for u in usuarios_a_purgar:
                info = f"  - Invitado #{u.id} ({u.email}) registrado {u.date_joined:%Y-%m-%d}"
                if dry:
                    self.stdout.write(self.style.WARNING(f"[SIMULADO] {info}"))
                else:
                    # Al eliminar el usuario, la cascada de Django elimina carritos y logs asociados
                    u.delete()
                    purgados_usuarios += 1

            # Purga adicional de carritos huérfanos sin items con última actualización anterior al corte
            carritos_huerfanos = Carrito.objects.filter(
                actualizado_en__lte=corte,
                items__isnull=True
            )
            total_carritos_huerfanos = carritos_huerfanos.count()

            if dry:
                self.stdout.write(self.style.WARNING(
                    f"[SIMULADO] Carritos vacíos huérfanos a purgar: {total_carritos_huerfanos}"
                ))
            else:
                carritos_huerfanos.delete()

        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"[SIMULACIÓN COMPLETADA] Se habrían purgado {len(usuarios_a_purgar)} cuentas y {total_carritos_huerfanos} carritos huérfanos."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"[PURGA EXITOSA] Se eliminaron {purgados_usuarios} cuentas de invitados y {total_carritos_huerfanos} carritos abandonados."
            ))
