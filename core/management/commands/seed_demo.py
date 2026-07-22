from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from accounts.models import CustomUser, PerfilCliente, PerfilVendedor
from appointments.models import BloqueHorario, Tecnologo
from core.models import Sucursal
from store.models import Categoria, Producto

def _norm_rut(rut):
    if not rut: return rut
    return rut.strip().upper().replace('.', '').replace('-', '').replace(' ', '')

class Command(BaseCommand):
    help = 'Carga datos de demostracion.'
    @transaction.atomic
    def handle(self, *args, **options):
        hoy = timezone.now().date()
        sucursales = {}
        for nombre, direccion, telefono in [
            ('Sucursal Central - Providencia', 'Av. Providencia 1234, Providencia', '+56 2 2345 6789'),
            ('Sucursal Santiago Centro', 'Ahumada 312, Santiago', '+56 2 2234 5678'),
        ]:
            obj, _ = Sucursal.objects.get_or_create(nombre=nombre, defaults={'direccion': direccion, 'telefono': telefono})
            sucursales[nombre] = obj
        categorias = {}
        for nombre, slug, desc in [
            ('Armazones Opticos', 'armazones-opticos', 'Armazones opticos y de lectura.'),
            ('Lentes de Sol', 'lentes-de-sol', 'Lentes de sol con proteccion UV.'),
            ('Lentes de Contacto', 'lentes-de-contacto', 'Lentes de contacto y soluciones.'),
        ]:
            obj, _ = Categoria.objects.get_or_create(slug=slug, defaults={'nombre': nombre, 'descripcion': desc})
            categorias[slug] = obj
        for nombre, slug_cat, precio, stock in [
            ('Armazon Titanium Matiz Titan Pro Flex', 'armazones-opticos', 45900, 8),
            ('Armazon Acetato Clasico Matiz', 'armazones-opticos', 39900, 5),
            ('Lentes Solar Polarized Matiz UV400', 'lentes-de-sol', 62000, 3),
            ('Lentes de Sol Aviador Polarizado', 'lentes-de-sol', 71000, 6),
            ('Lentes de Contacto Mensuales (caja x6)', 'lentes-de-contacto', 28900, 20),
        ]:
            Producto.objects.update_or_create(nombre=nombre, categoria=categorias[slug_cat], defaults={'precio': precio, 'stock': stock})
        tecnologos = []
        for nombre, rut, esp, suc in [
            ('TM. Andrea Silva', '12345678-5', 'Refraccion', 'Sucursal Central - Providencia'),
            ('TM. Roberto Gomez', '98765432-1', 'Especialista en Baja Vision', 'Sucursal Santiago Centro'),
        ]:
            obj, _ = Tecnologo.objects.get_or_create(rut=_norm_rut(rut), defaults={'nombre': nombre, 'especialidad': esp, 'sucursal': sucursales[suc]})
            tecnologos.append(obj)
        fechas = [hoy + timedelta(days=i) for i in (0, 1, 2, 3)]
        horas = [(time(9, 0), time(10, 0)), (time(10, 0), time(11, 0)), (time(11, 0), time(12, 0)), (time(12, 0), time(13, 0))]
        for tec in tecnologos:
            for fecha in fechas:
                for hi, hf in horas:
                    BloqueHorario.objects.get_or_create(tecnologo=tec, fecha=fecha, hora_inicio=hi, defaults={'hora_fin': hf, 'disponible': True})
        cli = CustomUser.objects.filter(email='cliente@prueba.cl').first()
        if not cli:
            cli = CustomUser.objects.create_user(email='cliente@prueba.cl', password='Password123!', first_name='Juan', last_name='Perez', role='CLIENTE')
        PerfilCliente.objects.get_or_create(user=cli, defaults={'rut': _norm_rut('11111111-1'), 'telefono': '+56912345678', 'direccion': 'Av. Prueba 123, Santiago'})
        ven = CustomUser.objects.filter(email='vendedor@prueba.cl').first()
        if not ven:
            ven = CustomUser.objects.create_user(email='vendedor@prueba.cl', password='Password123!', first_name='Vendedor', last_name='Demo', role='VENDEDOR')
        PerfilVendedor.objects.get_or_create(user=ven, defaults={'codigo_vendedor': 'V001', 'sucursal': sucursales['Sucursal Central - Providencia']})
        self.stdout.write(self.style.SUCCESS('seed_demo OK (bloques incluyen HOY).'))
        self.stdout.write(self.style.WARNING('Cliente: cliente@prueba.cl / Password123!  |  Vendedor: vendedor@prueba.cl / Password123!'))