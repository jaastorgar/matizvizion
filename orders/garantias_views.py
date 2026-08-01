"""
Garantias: dos caras del mismo calculo puro.
- GarantiasClienteView: el cliente ve el certificado de SUS compras entregadas.
- GarantiasMarcoView:   el staff (VENDEDOR/ADMIN) ve el marco aplicable a una
  orden concreta para resolver una devolucion con el reglamento delante.
El reloj se ancla a Orden.fecha_entrega; si no existe (orden entregada antes
de ese campo), se usa actualizado_en como respaldo sin inventar datos.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsVendedorUser
from .models import Orden, PoliticaGarantia

ESTADOS_CON_ENTREGA = ['ENVIADA', 'ENTREGADA', 'DEVUELTA']


def _fecha_ancla(orden):
    return orden.fecha_entrega or (orden.actualizado_en.date() if orden.actualizado_en else None)


def _vigencia(politica, ancla, hoy):
    vence = ancla + timedelta(days=politica.plazo_dias_max)
    return vence, (vence - hoy).days


def _serializar_garantias(ancla, hoy):
    out = []
    if not ancla:
        return out
    for pol in PoliticaGarantia.objects.filter(activa=True).order_by('orden_prioridad', 'nombre'):
        vence, dias = _vigencia(pol, ancla, hoy)
        out.append({
            'codigo': pol.codigo,
            'nombre': pol.nombre,
            'base': pol.base,
            'descripcion': pol.descripcion,
            'exclusiones': pol.exclusiones,
            'plazo_label': pol.plazo_label,
            'vence_en': vence.isoformat(),
            'dias_restantes': dias,
            'plazo_dias_max': pol.plazo_dias_max,
            'vigente': dias >= 0,
            'permite_devolucion': pol.permite_devolucion,
            'permite_cambio': pol.permite_cambio,
            'permite_reparacion': pol.permite_reparacion,
            'permite_rehacer': pol.permite_rehacer,
        })
    return out


def _bloque_orden(orden, hoy):
    ancla = _fecha_ancla(orden)
    return {
        'codigo': orden.codigo,
        'estado': orden.estado,
        'fecha_entrega': ancla.isoformat() if ancla else None,
        'fecha_entrega_real': bool(orden.fecha_entrega),
        'pendiente_entrega': (orden.estado == 'ENVIADA' and not orden.fecha_entrega),
        'garantias': _serializar_garantias(ancla, hoy),
    }


class GarantiasClienteView(APIView):
    """Solo el cliente ve sus propias compras; filtra por request.user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = timezone.localdate()
        ordenes = Orden.objects.filter(
            cliente=request.user, estado__in=ESTADOS_CON_ENTREGA
        ).order_by('-creado_en')
        return Response([_bloque_orden(o, hoy) for o in ordenes])


class GarantiasMarcoView(APIView):
    """
    Staff: marco de garantia aplicable a una orden concreta. Alimenta la mesa
    de resolucion de devoluciones del panel (vigencia + resoluciones permitidas).
    """
    permission_classes = [IsAuthenticated, IsVendedorUser]

    def get(self, request):
        orden_id = request.query_params.get('orden')
        if not orden_id:
            return Response({'error': 'Indica la orden (?orden=ID).'}, status=400)
        try:
            orden = Orden.objects.get(pk=orden_id)
        except (Orden.DoesNotExist, ValueError):
            return Response({'error': 'Orden no encontrada.'}, status=404)
        return Response(_bloque_orden(orden, timezone.localdate()))