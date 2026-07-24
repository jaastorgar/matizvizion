"""
Centro de correos transaccionales de Matizvision.
Cada notify_* renderiza un template y envia con fail_silently=True para que
un fallo de SMTP NUNCA rompa el flujo de negocio. Usar dentro de
transaction.on_commit(...) cuando se llama desde un cambio de estado.
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

ORDEN_LABEL = {
    'PAGADA': ('recibida', 'Pago recibido'),
    'EN_PREPARACION': ('en_preparacion', 'En preparacion'),
    'ENVIADA': ('enviada', 'Enviada'),
    'LISTO_PARA_RETIRO': ('lista_retiro', 'Lista para retiro'),
    'ENTREGADA': ('entregada', 'Entregada'),
    'CANCELADA': ('cancelada', 'Cancelada'),
    'DEVUELTA': ('devuelta', 'Devuelta'),
}
CITA_LABEL = {
    'agendada': 'agendada',
    'reagendada': 'reagendada',
    'cancelada': 'cancelada',
    'completada': 'completada',
}


def _from_email():
    return getattr(settings, 'DEFAULT_FROM_EMAIL', 'Matizvision <no-reply@matizvision.cl>')


def _send(subject, template, context, to_email):
    if not to_email:
        return
    try:
        body = render_to_string(template, context)
        send_mail(subject, body, _from_email(), [to_email], fail_silently=True)
    except Exception as e:
        logger.error('No se pudo enviar mail a %s: %s', to_email, e)


def _money(n):
    try:
        return '${:,}'.format(int(Decimal(str(n))))
    except Exception:
        return str(n)


def notify_password_reset(user, reset_url):
    nombre = ((user.first_name or '') + ' ' + (user.last_name or '')).strip() or 'Hola'
    _send(
        'Recupera tu contrasena - Matizvision',
        'emails/password_reset.txt',
        {'nombre': nombre, 'email': user.email, 'reset_url': reset_url,
         'es_invitado': getattr(user, 'is_guest', False)},
        user.email,
    )


def notify_datos_actualizados(user):
    nombre = ((user.first_name or '') + ' ' + (user.last_name or '')).strip() or 'Hola'
    _send(
        'Tus datos fueron actualizados - Matizvision',
        'emails/datos.txt',
        {'nombre': nombre, 'email': user.email},
        user.email,
    )


def notify_orden(orden, estado):
    info = ORDEN_LABEL.get(estado)
    if not info:
        return
    clave, label = info
    items = []
    for it in orden.items.select_related('producto').all():
        items.append({
            'nombre': it.producto.nombre,
            'sku': getattr(it.producto, 'sku', '') or '',
            'cantidad': it.cantidad,
            'subtotal': _money(it.subtotal),
        })
    _send(
        f'Tu pedido {orden.codigo or ("#" + str(orden.id))}: {label} - Matizvision',
        'emails/orden_estado.txt',
        {
            'codigo': orden.codigo or ('#' + str(orden.id)),
            'estado_clave': clave,
            'estado_label': label,
            'email': orden.cliente.email,
            'items': items,
            'total': _money(orden.total),
        },
        orden.cliente.email,
    )


def notify_cita(cita, evento):
    label = CITA_LABEL.get(evento)
    if not label:
        return
    b = cita.bloque
    _send(
        f'Tu cita fue {label} - Matizvision',
        'emails/cita.txt',
        {
            'evento': evento,
            'email': cita.cliente.email,
            'fecha': b.fecha,
            'hora': str(b.hora_inicio)[:5],
            'tecnologo': b.tecnologo.nombre,
            'sucursal': b.tecnologo.sucursal.nombre,
        },
        cita.cliente.email,
    )