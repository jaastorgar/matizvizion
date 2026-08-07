from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Elimina TODOS los datos en cascada, modelo por modelo, en orden seguro de dependencias.'

    def add_arguments(self, parser):
        parser.add_argument('--si', action='store_true', help='Omite la confirmacion interactiva.')
        parser.add_argument('--incluye-admins', action='store_true',
                            help='Elimina tambien usuarios ADMIN/superuser (quedaras sin sesion).')

    def handle(self, *args, **options):
        if not options['si']:
            resp = input('Esto borrara TODOS los datos del sistema. Escribe BORRAR para continuar: ')
            if resp.strip().upper() != 'BORRAR':
                self.stdout.write(self.style.WARNING('Operacion cancelada.'))
                return

        from accounts.models import CustomUser, PerfilCliente, PerfilVendedor
        from appointments.models import BloqueHorario, CitaMedica, Tecnologo
        from core.models import Sucursal
        from orders import models as om
        from store.models import Categoria, Producto, RecetaOptica

        # Orden seguro: hijos antes que padres (evita ProtectedError y dobles borrados)
        pasos = [
            ('HistorialEstado', om.HistorialEstado),
            ('SolicitudDevolucion', om.SolicitudDevolucion),
        ]
        if hasattr(om, 'PoliticaGarantia'):
            pasos.append(('PoliticaGarantia', om.PoliticaGarantia))
        pasos += [
            ('ItemOrden', om.ItemOrden),
            ('Orden', om.Orden),
            ('ItemCarrito', om.ItemCarrito),
            ('Carrito', om.Carrito),
            ('CitaMedica', CitaMedica),        # libera bloques (PROTECT) antes de borrarlos
            ('BloqueHorario', BloqueHorario),
            ('RecetaOptica', RecetaOptica),
            ('Tecnologo', Tecnologo),
            ('Producto', Producto),            # antes que Categoria (FK) y antes que ItemOrden (PROTECT ya borrado)
            ('Categoria', Categoria),
            ('Sucursal', Sucursal),
            ('PerfilCliente', PerfilCliente),
            ('PerfilVendedor', PerfilVendedor),
        ]

        with transaction.atomic():
            for nombre, model in pasos:
                n, _ = model.objects.all().delete()
                self.stdout.write(f'  - {nombre}: {n} eliminado(s).')

            usuarios = CustomUser.objects.all()
            if not options['incluye_admins']:
                usuarios = usuarios.exclude(role='ADMIN').exclude(is_superuser=True)
                self.stdout.write('  (se conservan ADMIN/superuser; usa --incluye-admins para borrarlos)')
            n, _ = usuarios.delete()
            self.stdout.write(f'  - CustomUser: {n} eliminado(s).')

        self.stdout.write(self.style.SUCCESS('Limpieza en cascada completada.'))
        self.stdout.write(self.style.WARNING('Si borraste catalogo/clinicos, vuelve a sembrar con: python manage.py seed_garantias (y tu seed de datos).'))