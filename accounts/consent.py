"""
Consentimientos (Ley 21.719 / Ley 19.496).
Helpers centralizados para sellar, consultar y auditar los consentimientos del usuario.
"""
from django.utils import timezone

VERSION_CONSENTIMIENTO = '2026-08'
ERROR_CONSENTIMIENTO_SALUD = 'CONSENTIMIENTO_SALUD_REQUERIDO'


def get_client_ip(request):
    """Obtiene la IP remota del cliente respetando proxies/cabeceras."""
    if not request:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_consentimiento_log(user, tipo, accion, request=None, version=VERSION_CONSENTIMIENTO):
    """
    Crea un registro de auditoría inmutable en ConsentimientoLog.
    """
    from accounts.models import ConsentimientoLog
    ip = get_client_ip(request)
    ua = ''
    if request:
        ua = (request.META.get('HTTP_USER_AGENT') or '')[:500]

    email_snapshot = getattr(user, 'email', '')
    return ConsentimientoLog.objects.create(
        usuario=user,
        email_snapshot=email_snapshot,
        tipo=tipo,
        accion=accion,
        version=version,
        ip_address=ip,
        user_agent=ua
    )


def sellar_terminos(user, request=None):
    user.acepta_terminos = True
    user.acepta_terminos_en = timezone.now()
    user.acepta_terminos_version = VERSION_CONSENTIMIENTO
    registrar_consentimiento_log(user, 'TERMINOS', 'OTORGADO', request=request)


def sellar_salud(user, request=None):
    user.consiente_salud = True
    user.consiente_salud_en = timezone.now()
    user.consiente_salud_version = VERSION_CONSENTIMIENTO
    registrar_consentimiento_log(user, 'SALUD', 'OTORGADO', request=request)


def revocar_salud(user, request=None):
    user.consiente_salud = False
    user.consiente_salud_en = None
    registrar_consentimiento_log(user, 'SALUD', 'REVOCADO', request=request)


def actualizar_marketing(user, consiente: bool, request=None):
    user.consiente_marketing = bool(consiente)
    accion = 'OTORGADO' if consiente else 'REVOCADO'
    registrar_consentimiento_log(user, 'MARKETING', accion, request=request)


def requiere_salud(user):
    return bool(getattr(user, 'consiente_salud', False))


def consent_payload(user):
    return {
        'acepta_terminos': getattr(user, 'acepta_terminos', False),
        'acepta_terminos_en': getattr(user, 'acepta_terminos_en', None),
        'acepta_terminos_version': getattr(user, 'acepta_terminos_version', ''),
        'consiente_salud': getattr(user, 'consiente_salud', False),
        'consiente_salud_en': getattr(user, 'consiente_salud_en', None),
        'consiente_salud_version': getattr(user, 'consiente_salud_version', ''),
        'consiente_marketing': getattr(user, 'consiente_marketing', False),
        'version_vigente': VERSION_CONSENTIMIENTO,
    }