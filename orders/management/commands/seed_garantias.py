"""
Siembra/actualiza las politicas de garantia del PDF de Matiz Vision.
Idempotente (update_or_create por codigo).
Ejecutar: python manage.py seed_garantias
"""
from django.core.management.base import BaseCommand

from orders.models import PoliticaGarantia

EXCLUSIONES_GENERALES = (
    "Ralladuras por friccion o mal uso; roturas por caidas o aplastamiento; "
    "limpieza con sustancias abrasivas; exposicion a calor extremo (ej. tablero de automovil)."
)

POLITICAS = [
    {
        'codigo': 'legal',
        'nombre': 'Garantía Legal (Ley 19.496 - SERNAC)',
        'base': 'LEGAL',
        'orden_prioridad': 1,
        'plazo_label': '6 meses',
        'plazo_dias_min': 180,
        'plazo_dias_max': 180,
        'descripcion': (
            "Fallas de origen, imperfecciones de fabricacion, soldaduras o bisagras "
            "defectuosas. Opcion triple (6x3) a eleccion del cliente: devolucion del "
            "dinero, cambio directo o reparacion gratuita."
        ),
        'exclusiones': EXCLUSIONES_GENERALES,
        'permite_devolucion': True,
        'permite_cambio': True,
        'permite_reparacion': True,
        'permite_rehacer': False,
        'solo_con_receta': False,
        'activa': True,
    },
    {
        'codigo': 'tecnica_armazon',
        'nombre': 'Garantía Técnica - Armazones',
        'base': 'FABRICANTE',
        'orden_prioridad': 2,
        'plazo_label': '12 meses',
        'plazo_dias_min': 365,
        'plazo_dias_max': 365,
        'descripcion': (
            "Desprendimiento de soldaduras, fallas espontaneas en bisagras o "
            "decoloracion anomala por defecto del material del armazon."
        ),
        'exclusiones': EXCLUSIONES_GENERALES,
        'permite_devolucion': False,
        'permite_cambio': True,
        'permite_reparacion': True,
        'permite_rehacer': False,
        'solo_con_receta': False,
        'activa': True,
    },
    {
        'codigo': 'tecnica_tratamiento',
        'nombre': 'Garantía Técnica - Tratamientos',
        'base': 'FABRICANTE',
        'orden_prioridad': 3,
        'plazo_label': '6 a 12 meses',
        'plazo_dias_min': 180,
        'plazo_dias_max': 365,
        'descripcion': (
            "Craquelado, ampollamiento o desprendimiento espontaneo del Antirreflejo, "
            "Filtro Azul o viraje Fotocromatico."
        ),
        'exclusiones': EXCLUSIONES_GENERALES,
        'permite_devolucion': False,
        'permite_cambio': True,
        'permite_reparacion': True,
        'permite_rehacer': False,
        'solo_con_receta': False,
        'activa': True,
    },
    {
        'codigo': 'adaptacion',
        'nombre': 'Garantía de Adaptación Óptica (Confort Visual)',
        'base': 'CONFORT',
        'orden_prioridad': 4,
        'plazo_label': '30 a 60 días',
        'plazo_dias_min': 30,
        'plazo_dias_max': 60,
        'descripcion': (
            "Revision y ajuste de graduacion sin costo. En lentes multifocales no "
            "adaptados, se re-hacen en dos pares monofocales (cerca/lejos) o un "
            "bifocal de igual valor."
        ),
        'exclusiones': "Cambio de gusto estetico; receta externa no verificada por la optica.",
        'permite_devolucion': False,
        'permite_cambio': False,
        'permite_reparacion': True,
        'permite_rehacer': True,
        'solo_con_receta': True,
        'activa': True,
    },
]


class Command(BaseCommand):
    help = 'Siembra/actualiza las politicas de garantia del PDF (idempotente).'

    def handle(self, *args, **options):
        n = 0
        for data in POLITICAS:
            codigo = data['codigo']
            _, created = PoliticaGarantia.objects.update_or_create(codigo=codigo, defaults=data)
            n += 1
            self.stdout.write(f"  {'creada' if created else 'actualizada'}: {codigo}")
        self.stdout.write(self.style.SUCCESS(f'Seed de garantias listo: {n} politicas.'))