from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, PerfilCliente
from .permissions import IsClienteUser
from .serializers import PerfilClienteSerializer, RegistroClienteSerializer


class RegistroClienteView(generics.CreateAPIView):
    serializer_class = RegistroClienteSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    """Datos basicos del usuario autenticado (incluye is_guest)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'is_guest': getattr(u, 'is_guest', False),
            'is_superuser': getattr(u, 'is_superuser', False),
            'telefono': getattr(u, 'telefono', ''),
            'direccion': getattr(u, 'direccion', ''),
            'comuna': getattr(u, 'comuna', ''),
            'region': getattr(u, 'region', ''),
        })


    def patch(self, request):
        # [mv] actualiza el perfil propio (nombre, apellido y datos de contacto)
        u = request.user
        for f in ['first_name', 'last_name', 'telefono', 'direccion', 'comuna', 'region']:
            if f in request.data:
                setattr(u, f, (request.data.get(f) or '').strip())
        u.save()
        return Response({
            'id': u.id, 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
            'role': u.role, 'is_guest': getattr(u, 'is_guest', False), 'is_superuser': getattr(u, 'is_superuser', False),
            'telefono': getattr(u, 'telefono', ''), 'direccion': getattr(u, 'direccion', ''),
            'comuna': getattr(u, 'comuna', ''), 'region': getattr(u, 'region', ''),
        })

class ConsentimientosView(APIView):
    """Lectura y actualizacion de consentimientos del usuario autenticado con auditoría."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .consent import consent_payload
        return Response(consent_payload(request.user))

    def patch(self, request):
        from .consent import (
            consent_payload, sellar_salud, revocar_salud,
            actualizar_marketing, sellar_terminos
        )
        u = request.user
        if 'acepta_terminos' in request.data:
            if bool(request.data.get('acepta_terminos')) and not u.acepta_terminos:
                sellar_terminos(u, request=request)
        if 'consiente_salud' in request.data:
            val = bool(request.data.get('consiente_salud'))
            if val and not u.consiente_salud:
                sellar_salud(u, request=request)
            elif not val and u.consiente_salud:
                revocar_salud(u, request=request)
        if 'consiente_marketing' in request.data:
            val = bool(request.data.get('consiente_marketing'))
            if val != u.consiente_marketing:
                actualizar_marketing(u, val, request=request)
        u.save()
        return Response(consent_payload(u))


class MiPerfilView(APIView):
    """
    Perfil de cliente con UPSERT: si el usuario (p.ej. un invitado) aun no
    tiene PerfilCliente, el GET devuelve campos vacios y el PUT/PATCH lo crea.
    """
    permission_classes = [IsAuthenticated, IsClienteUser]

    def get(self, request):
        try:
            perfil = request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            return Response({'rut': '', 'telefono': '', 'direccion': '', 'comuna': '', 'region': ''})
        return Response(PerfilClienteSerializer(perfil).data)

    def put(self, request):
        return self._upsert(request, partial=False)

    def patch(self, request):
        return self._upsert(request, partial=True)

    def _upsert(self, request, partial):
        try:
            perfil = request.user.perfil_cliente
        except PerfilCliente.DoesNotExist:
            perfil = None
        ser = PerfilClienteSerializer(perfil, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        if perfil is None:
            try:
                perfil = ser.save(user=request.user)
            except IntegrityError:
                return Response(
                    {'rut': 'Ese RUT ya esta registrado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            ser.save()
        return Response(PerfilClienteSerializer(perfil).data)


class GuestView(APIView):
    """
    Compra como invitado: crea (o reusa) un usuario sin contraseña a partir
    del email y devuelve un JWT. No crea PerfilCliente (se pedira despues).
    - email invalido            -> 400
    - email ya es cuenta real   -> 409 (debe iniciar sesion)
    - email ya es invitado      -> reusa y emite token (no duplica)
    - email nuevo               -> crea invitado y emite token
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'email': 'Debes indicar un correo electrónico.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response(
                {'email': 'El correo electrónico no es válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = CustomUser.objects.filter(email=email).first()
        if existing:
            if existing.has_usable_password():
                return Response(
                    {'email': 'Ese correo ya tiene una cuenta. Inicia sesión.'},
                    status=status.HTTP_409_CONFLICT,
                )
            tiene_perfil = hasattr(existing, 'perfil_cliente') and bool(getattr(existing.perfil_cliente, 'rut', ''))
            tiene_ordenes = existing.ordenes.exclude(estado__in=['PENDIENTE', 'CANCELADA', 'FALLIDA']).exists()
            tiene_recetas = hasattr(existing, 'recetas') and existing.recetas.exists()
            if tiene_perfil or tiene_ordenes or tiene_recetas:
                return Response(
                    {'email': 'Este correo ya tiene compras o datos registrados. Por tu seguridad, inicia sesión o recupera tu contraseña.'},
                    status=status.HTTP_409_CONFLICT,
                )
            user = existing
            created = False
        else:
            user = CustomUser.objects.create_guest(email=email)
            created = True

        token = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(token.access_token),
                'refresh': str(token),
                'is_guest': user.is_guest,
                'role': user.role,
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ExportarDatosPersonalesView(APIView):
    """
    Derecho de Portabilidad (Ley N° 21.719 / Estándar RGPD):
    Exporta una copia íntegra y estructurada (JSON) de todos los datos personales,
    consentimientos, recetas, citas clínicas y compras del usuario.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.utils import timezone
        from .consent import consent_payload
        from orders.models import Orden
        from store.models import RecetaOptica
        from recetas.models import Receta
        from appointments.models import CitaMedica

        perfil = getattr(user, 'perfil_cliente', None)
        datos_perfil = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'rut': getattr(perfil, 'rut', ''),
            'telefono': getattr(perfil, 'telefono', '') or getattr(user, 'telefono', ''),
            'direccion': getattr(perfil, 'direccion', '') or getattr(user, 'direccion', ''),
            'comuna': getattr(perfil, 'comuna', '') or getattr(user, 'comuna', ''),
            'region': getattr(perfil, 'region', '') or getattr(user, 'region', ''),
            'role': user.role,
            'fecha_registro': user.date_joined.isoformat() if user.date_joined else None,
        }

        recetas_opticas = []
        if perfil:
            for ro in RecetaOptica.objects.filter(cliente=perfil):
                recetas_opticas.append({
                    'id': ro.id,
                    'esfera_od': float(ro.esfera_od) if ro.esfera_od is not None else None,
                    'esfera_oi': float(ro.esfera_oi) if ro.esfera_oi is not None else None,
                    'cilindro_od': float(ro.cilindro_od) if ro.cilindro_od is not None else None,
                    'cilindro_oi': float(ro.cilindro_oi) if ro.cilindro_oi is not None else None,
                    'eje_od': ro.eje_od,
                    'eje_oi': ro.eje_oi,
                    'add_od': float(ro.add_od) if ro.add_od is not None else None,
                    'add_oi': float(ro.add_oi) if ro.add_oi is not None else None,
                    'observaciones': ro.observaciones or '',
                    'creado_en': ro.creado_en.isoformat(),
                })

        recetas_digitales = []
        for r in Receta.objects.filter(cliente=user):
            recetas_digitales.append({
                'id': r.id,
                'nombre': r.nombre,
                'tipo': r.get_tipo_display(),
                'detalle': r.detalle,
                'vigencia_hasta': r.vigencia_hasta.isoformat() if r.vigencia_hasta else None,
                'estado': r.estado,
                'subido_en': r.creado_en.isoformat(),
            })

        citas = []
        for c in CitaMedica.objects.filter(cliente=user).select_related('bloque__tecnologo__sucursal'):
            b = c.bloque
            citas.append({
                'id': c.id,
                'estado': c.get_estado_display(),
                'fecha': b.fecha.isoformat(),
                'hora_inicio': str(b.hora_inicio)[:5],
                'hora_fin': str(b.hora_fin)[:5],
                'tecnologo': b.tecnologo.nombre,
                'sucursal': b.tecnologo.sucursal.nombre if b.tecnologo.sucursal else '',
                'fecha_reserva': c.fecha_reserva.isoformat() if c.fecha_reserva else None,
            })

        ordenes = []
        for o in Orden.objects.filter(cliente=user).prefetch_related('items__producto'):
            items = []
            for it in o.items.all():
                items.append({
                    'producto': it.producto.nombre,
                    'sku': getattr(it.producto, 'sku', '') or '',
                    'cantidad': it.cantidad,
                    'precio_unitario': float(it.precio_unitario or 0),
                    'tipo_lente': it.get_tipo_lente_display(),
                    'uso_lente': it.get_uso_lente_display(),
                })
            ordenes.append({
                'codigo': o.codigo,
                'estado': o.get_estado_display(),
                'total': float(o.total or 0),
                'modo_pago': o.modo_pago,
                'fecha': o.creado_en.isoformat(),
                'items': items,
            })

        historial_consentimientos = []
        for log in user.logs_consentimiento.all().order_by('-creado_en'):
            historial_consentimientos.append({
                'id': log.id,
                'tipo': log.get_tipo_display(),
                'accion': log.get_accion_display(),
                'version': log.version,
                'ip': log.ip_address,
                'fecha': log.creado_en.isoformat(),
            })

        data = {
            'leyenda': 'Exportación de Datos Personales conforme al Derecho de Portabilidad (Ley N° 21.719, Chile)',
            'exportado_en': timezone.now().isoformat(),
            'perfil': datos_perfil,
            'consentimientos': consent_payload(user),
            'historial_auditoria_consentimientos': historial_consentimientos,
            'recetas_opticas_graduacion': recetas_opticas,
            'recetas_digitales': recetas_digitales,
            'citas_clinicas': citas,
            'compras_y_pedidos': ordenes,
        }
        return Response(data)


class SolicitudSupresionView(APIView):
    """
    Derecho de Supresión / Derecho al Olvido (Ley N° 21.719):
    Permite al titular solicitar la supresión de sus datos de contacto y comerciales.

    Resguardos Legales Obligatorios en Chile:
    1. Ley 20.584 y D.S. 41 del MINSAL: Las prescripciones ópticas y recetas médicas
       deben ser retenidas por un plazo mínimo de 15 años bajo custodia legal confidencial.
    2. Código Tributario y Ley de Impuesto a la Renta (SII): La documentación tributaria
       (boletas, facturas) debe conservarse por un mínimo de 6 años para efectos de fiscalización.

    Efectos de la solicitud:
    - Valida que no existan pedidos pendientes en tránsito o citas médicas activas.
    - Revoca todos los consentimientos otorgados (términos, salud, marketing) registrando auditoría.
    - Desactiva el acceso a la cuenta (is_active=False) e inutiliza contraseñas.
    - Anonimiza datos de contacto y despacho (nombre, apellido, teléfono, dirección, comuna, región).
    - Desvincula el correo electrónico sustituyéndolo por un identificador anónimo cifrado.
    - Genera constancia en SolicitudSupresion con IP y fecha para rendición de cuentas (Accountability).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_staff or user.is_superuser:
            return Response(
                {'detail': 'Las cuentas de administración o personal no pueden suprimirse por esta vía.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from orders.models import EstadoOrden
        pedidos_activos = user.ordenes.filter(
            estado__in=[
                EstadoOrden.PAGADA,
                EstadoOrden.EN_PREPARACION,
                EstadoOrden.LISTO_PARA_RETIRO,
                EstadoOrden.ENVIADA,
            ]
        ).exists()
        if pedidos_activos:
            return Response(
                {
                    'detail': 'Tienes pedidos en proceso de preparación o despacho. Una vez recibidos tus productos podrás solicitar la supresión de tu cuenta.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        citas_activas = user.citas.filter(estado__in=['AGENDADA', 'CONFIRMADA']).exists()
        if citas_activas:
            return Response(
                {
                    'detail': 'Tienes citas de optometría agendadas activas. Cancélalas antes de solicitar la baja de tu cuenta.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = (request.data.get('motivo') or '').strip()
        email_original = user.email
        perfil = getattr(user, 'perfil_cliente', None)
        rut_original = getattr(perfil, 'rut', '') if perfil else ''

        # Registrar la solicitud formal de supresión
        from .models import SolicitudSupresion
        from .consent import get_client_ip, registrar_consentimiento_log
        import uuid

        ip = get_client_ip(request)
        ua = (request.META.get('HTTP_USER_AGENT') or '')[:500]

        SolicitudSupresion.objects.create(
            usuario=user,
            email_original=email_original,
            rut_asociado=rut_original,
            ip_address=ip,
            user_agent=ua,
            motivo=motivo,
        )

        # Revocar consentimientos en auditoría
        registrar_consentimiento_log(user, 'TERMINOS', 'REVOCADO', request=request)
        registrar_consentimiento_log(user, 'SALUD', 'REVOCADO', request=request)
        registrar_consentimiento_log(user, 'MARKETING', 'REVOCADO', request=request)

        # Anonimizar datos de usuario
        user.is_active = False
        user.set_unusable_password()
        user.acepta_terminos = False
        user.consiente_salud = False
        user.consiente_marketing = False
        user.first_name = 'Usuario'
        user.last_name = 'Anonimizado'
        user.telefono = ''
        user.direccion = ''
        user.comuna = ''
        user.region = ''
        user.email = f"suprimido_{user.id}_{uuid.uuid4().hex[:8]}@anon.matizvision.cl"
        user.save()

        # Anonimizar perfil de cliente
        if perfil:
            perfil.telefono = ''
            perfil.direccion = ''
            perfil.comuna = ''
            perfil.region = ''
            tiene_recetas = (hasattr(perfil, 'recetas') and perfil.recetas.exists()) or (hasattr(user, 'recetas') and user.recetas.exists())
            tiene_ordenes = user.ordenes.exists()
            if not tiene_recetas and not tiene_ordenes:
                perfil.rut = f"SUP-{user.id}"
            perfil.save()

        return Response({
            'ok': True,
            'mensaje': (
                'Tu cuenta ha sido desactivada y tus datos de contacto y preferencias han sido anonimizados exitosamente. '
                'Conforme a la Ley N° 20.584 y la normativa tributaria chilena, los antecedentes clínicos y boletas previas '
                'se conservarán en archivo pasivo legal durante los plazos obligatorios de custodia.'
            )
        })
