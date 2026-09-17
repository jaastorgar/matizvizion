"""
Consentimientos (Ley 21.719 / Ley 19.496).
Helpers centralizados para sellar y consultar consentimientos del usuario.
"""
from django.utils import timezone

VERSION_CONSENTIMIENTO = '2026-08'
ERROR_CONSENTIMIENTO_SALUD = 'CONSENTIMIENTO_SALUD_REQUERIDO'


def sellar_terminos(user):
    user.acepta_terminos = True
    user.acepta_terminos_en = timezone.now()
    user.acepta_terminos_version = VERSION_CONSENTIMIENTO


def sellar_salud(user):
    user.consiente_salud = True
    user.consiente_salud_en = timezone.now()
    user.consiente_salud_version = VERSION_CONSENTIMIENTO


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