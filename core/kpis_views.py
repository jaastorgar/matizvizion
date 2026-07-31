"""
Endpoint de Inteligencia de Negocio (BI) para el panel de administración.
Solo accesible por ADMIN (IsAdminUserCustom).
GET /api/admin/kpis/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
"""
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db.models import Count, F, Sum, Value
from django.db.models.functions import Coalesce, TruncDay
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser
from accounts.permissions import IsAdminUserCustom
from appointments.models import CitaMedica
from orders.models import Orden, ItemOrden
from store.models import Producto

ESTADOS_VENTA = ['PAGADA', 'EN_PREPARACION', 'LISTO_PARA_RETIRO', 'ENVIADA', 'ENTREGADA']


class KpisView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def get(self, request):
        hoy = timezone.localdate()
        desde_str = request.query_params.get('desde')
        hasta_str = request.query_params.get('hasta')
        try:
            desde = date.fromisoformat(desde_str) if desde_str else hoy - timedelta(days=30)
            hasta = date.fromisoformat(hasta_str) if hasta_str else hoy
        except (ValueError, TypeError):
            desde = hoy - timedelta(days=30)
            hasta = hoy
        desde_dt = timezone.make_aware(datetime.combine(desde, time.min))
        hasta_dt = timezone.make_aware(datetime.combine(hasta, time.max))
        rango = {'creado_en__range': (desde_dt, hasta_dt)}
        rango_venta = {'estado__in': ESTADOS_VENTA, **rango}

        # --- KPIs ---
        agg = Orden.objects.filter(**rango_venta).aggregate(total=Sum('total'), n=Count('id'))
        ventas_totales = float(agg['total'] or 0)
        num_ordenes = agg['n'] or 0
        ticket_promedio = round(ventas_totales / num_ordenes, 2) if num_ordenes else 0
        citas_completadas = CitaMedica.objects.filter(
            estado='COMPLETADA', fecha_reserva__range=(desde_dt, hasta_dt)
        ).count()
        clientes_nuevos = CustomUser.objects.filter(
            role='CLIENTE', date_joined__range=(desde_dt, hasta_dt)
        ).count()
        clientes_invitados = CustomUser.objects.filter(
            is_guest=True, date_joined__range=(desde_dt, hasta_dt)
        ).count()
        umbral_global = getattr(settings, 'STOCK_ALERT_THRESHOLD', 5)
        productos_bajo_stock = Producto.objects.filter(activo=True).filter(
            stock__lte=Coalesce('stock_minimo', Value(umbral_global))
        ).count()

        # --- Series ---
        ventas_por_dia = list(
            Orden.objects.filter(**rango_venta)
            .annotate(dia=TruncDay('creado_en'))
            .values('dia')
            .annotate(total=Sum('total'))
            .order_by('dia')
        )
        for v in ventas_por_dia:
            v['dia'] = v['dia'].date().isoformat()
            v['total'] = float(v['total'] or 0)

        top_productos = list(
            ItemOrden.objects.filter(orden__estado__in=ESTADOS_VENTA, orden__creado_en__range=(desde_dt, hasta_dt))
            .values('producto__nombre')
            .annotate(cantidad=Sum('cantidad'))
            .order_by('-cantidad')[:5]
        )
        top_productos = [{'nombre': t['producto__nombre'], 'cantidad': t['cantidad']} for t in top_productos]

        ordenes_por_estado = list(
            Orden.objects.filter(**rango).values('estado').annotate(n=Count('id')).order_by('estado')
        )
        citas_por_estado = list(
            CitaMedica.objects.filter(fecha_reserva__range=(desde_dt, hasta_dt))
            .values('estado').annotate(n=Count('id')).order_by('estado')
        )

        return Response({
            'desde': desde.isoformat(),
            'hasta': hasta.isoformat(),
            'kpis': {
                'ventas_totales': ventas_totales,
                'num_ordenes': num_ordenes,
                'ticket_promedio': ticket_promedio,
                'citas_completadas': citas_completadas,
                'clientes_nuevos': clientes_nuevos,
                'clientes_invitados': clientes_invitados,
                'productos_bajo_stock': productos_bajo_stock,
            },
            'ventas_por_dia': ventas_por_dia,
            'top_productos': top_productos,
            'ordenes_por_estado': ordenes_por_estado,
            'citas_por_estado': citas_por_estado,
        })