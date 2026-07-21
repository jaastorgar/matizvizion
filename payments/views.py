import logging
import uuid
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from decouple import config
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Orden
from store.models import Producto

from .models import (
    EstadoTransaccion,
    LogPago,
    TransaccionWebpay,
)
from .serializers import (
    TransaccionWebpaySerializer,
    WebpayCreateSerializer,
    WebpayReturnSerializer,
)


logger = logging.getLogger(__name__)


try:
    from transbank.webpay.webpay_plus import WebpayPlus
    from transbank.webpay.webpay_plus.transaction import Transaction
except ImportError:
    WebpayPlus = None
    Transaction = None


def configurar_transbank():
    """
    Configura Transbank según entorno.
    """
    if Transaction is None or WebpayPlus is None:
        raise ImproperlyConfigured(
            'El paquete transbank-sdk no está instalado.'
        )

    environment = config('WEBPAY_ENVIRONMENT', default='Integration')
    commerce_code = config('WEBPAY_COMMERCE_CODE', default='')
    api_key = config('WEBPAY_API_KEY', default='')

    if not commerce_code or not api_key:
        raise ImproperlyConfigured(
            'Debes configurar WEBPAY_COMMERCE_CODE y WEBPAY_API_KEY.'
        )

    if environment == 'Production':
        WebpayPlus.configure_for_production(commerce_code, api_key)
    else:
        WebpayPlus.configure_for_integration(commerce_code, api_key)


def get_transaction():
    """
    Devuelve una instancia de Transaction con Transbank configurado.
    """
    configurar_transbank()
    return Transaction()


def response_value(response, key, default=None):
    """
    Permite leer valores de respuestas de Transbank que pueden venir
    como diccionario o como objeto.
    """
    if isinstance(response, dict):
        return response.get(key, default)

    return getattr(response, key, default)


def response_to_dict(response):
    """
    Convierte la respuesta de Transbank a un diccionario serializable.
    """
    if isinstance(response, dict):
        data = response
    elif hasattr(response, '__dict__'):
        data = vars(response)
    else:
        data = {'response': str(response)}

    return {
        str(key): str(value)
        for key, value in data.items()
        if not str(key).startswith('_')
    }


def revertir_stock(orden):
    """
    Revierte el stock de una orden fallida o rechazada.
    Debe ejecutarse dentro de una transacción atómica.
    """
    items = list(orden.items.select_related('producto').all())
    producto_ids = [item.producto_id for item in items]

    productos = {
        producto.pk: producto
        for producto in Producto.objects.select_for_update().filter(
            pk__in=producto_ids
        )
    }

    for item in items:
        producto = productos.get(item.producto_id)

        if producto:
            producto.stock = F('stock') + item.cantidad
            producto.save(update_fields=['stock'])


class WebpayCreateView(APIView):
    """
    Endpoint para inicializar el pago en Webpay Plus.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WebpayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        orden_id = serializer.validated_data['orden_id']

        try:
            orden = Orden.objects.get(
                id=orden_id,
                cliente=request.user,
                estado=Orden.Estado.PENDIENTE
            )
        except Orden.DoesNotExist:
            return Response(
                {
                    'error': 'Orden no encontrada o no está en estado PENDIENTE.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if orden.total <= 0:
            return Response(
                {
                    'error': 'La orden no tiene un monto válido para pagar.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return_url = config('WEBPAY_RETURN_URL', default='')

        if not return_url:
            return Response(
                {
                    'error': 'WEBPAY_RETURN_URL no está configurada.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        buy_order = f"ORD-{orden.id}-{uuid.uuid4().hex[:8]}"
        session_id = f"SESS-{request.user.id}-{orden.id}-{uuid.uuid4().hex[:8]}"
        amount = float(orden.total)

        try:
            tx = get_transaction()
            response = tx.create(
                buy_order,
                session_id,
                amount,
                return_url
            )
        except Exception as error:
            logger.error(f"Error creando transacción Webpay: {error}")
            return Response(
                {
                    'error': 'No se pudo iniciar la transacción en Transbank.'
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        token = response_value(response, 'token')
        url = response_value(response, 'url')

        if not token or not url:
            logger.error(
                f"Respuesta inválida de Transbank al crear transacción: {response}"
            )
            return Response(
                {
                    'error': 'Respuesta inválida de Transbank.'
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        transaccion = TransaccionWebpay.objects.create(
            orden=orden,
            buy_order=buy_order,
            session_id=session_id,
            token=token,
            amount=orden.total,
            status=EstadoTransaccion.INICIADA
        )

        LogPago.objects.create(
            transaccion=transaccion,
            evento=LogPago.Evento.CREATE,
            raw_response=response_to_dict(response)
        )

        return Response(
            {
                'url': url,
                'token': token,
                'transaccion': TransaccionWebpaySerializer(transaccion).data
            },
            status=status.HTTP_201_CREATED
        )


class WebpayReturnView(APIView):
    """
    Endpoint de retorno/confirmación de Webpay Plus.
    Debe ser público para recibir el token_ws.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data if request.data else request.query_params

        serializer = WebpayReturnSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        token_ws = serializer.validated_data['token_ws']

        try:
            transaccion = TransaccionWebpay.objects.select_for_update().select_related(
                'orden'
            ).get(token=token_ws)
        except TransaccionWebpay.DoesNotExist:
            return Response(
                {
                    'error': 'Transacción no encontrada.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        orden = transaccion.orden

        # Idempotencia: si ya fue procesada, no volver a procesar.
        if transaccion.status != EstadoTransaccion.INICIADA:
            return Response(
                {
                    'message': 'Transacción ya procesada previamente.',
                    'status': transaccion.status
                },
                status=status.HTTP_200_OK
            )

        try:
            tx = get_transaction()
            response = tx.commit(token_ws)
        except Exception as error:
            logger.error(f"Error confirmando pago Webpay: {error}")

            LogPago.objects.create(
                transaccion=transaccion,
                evento=LogPago.Evento.ERROR,
                raw_response={
                    'error': str(error)
                }
            )

            transaccion.status = EstadoTransaccion.ERROR
            transaccion.save(update_fields=['status', 'actualizado_en'])

            return Response(
                {
                    'error': 'No se pudo confirmar el pago en Transbank.'
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        LogPago.objects.create(
            transaccion=transaccion,
            evento=LogPago.Evento.COMMIT,
            raw_response=response_to_dict(response)
        )

        status_tbk = response_value(response, 'status')
        response_code = response_value(response, 'response_code')

        transaccion.response_code = response_code
        transaccion.authorization_code = str(
            response_value(response, 'authorization_code') or ''
        )
        transaccion.payment_type_code = str(
            response_value(response, 'payment_type_code') or ''
        )

        installments_number = response_value(response, 'installments_number')
        if installments_number is not None:
            try:
                transaccion.installments_number = int(installments_number)
            except (TypeError, ValueError):
                transaccion.installments_number = None

        installments_amount = response_value(response, 'installments_amount')
        if installments_amount is not None:
            try:
                transaccion.installments_amount = Decimal(str(installments_amount))
            except (InvalidOperation, TypeError, ValueError):
                transaccion.installments_amount = None

        # Validación de monto recibido desde Transbank
        response_amount = response_value(response, 'amount')
        if response_amount is not None:
            try:
                if Decimal(str(response_amount)) != transaccion.amount:
                    logger.warning(
                        f"Diferencia de monto en transacción {transaccion.token}. "
                        f"Esperado: {transaccion.amount}, recibido: {response_amount}"
                    )
            except (InvalidOperation, TypeError, ValueError):
                logger.warning(
                    f"No se pudo validar el monto recibido para la transacción {transaccion.token}."
                )

        if status_tbk == 'AUTHORIZED' and response_code == 0:
            transaccion.status = EstadoTransaccion.AUTHORIZED
            transaccion.save()

            if orden.estado == Orden.Estado.PENDIENTE:
                orden.cambiar_estado(
                    nuevo_estado=Orden.Estado.PAGADA,
                    usuario=None
                )
            elif orden.estado != Orden.Estado.PAGADA:
                logger.warning(
                    f"La orden {orden.id} estaba en estado {orden.estado} "
                    f"cuando se autorizó la transacción {transaccion.token}."
                )

            return Response(
                {
                    'message': 'Pago exitoso.',
                    'orden_id': orden.id,
                    'status': transaccion.status
                },
                status=status.HTTP_200_OK
            )

        # Flujo rechazado o fallido
        transaccion.status = (
            EstadoTransaccion.RECHAZADA
            if status_tbk
            else EstadoTransaccion.FALLIDA
        )
        transaccion.save()

        if orden.estado == Orden.Estado.PENDIENTE:
            orden.cambiar_estado(
                nuevo_estado=Orden.Estado.FALLIDA,
                usuario=None
            )
            revertir_stock(orden)

        return Response(
            {
                'message': 'Pago rechazado o fallido.',
                'orden_id': orden.id,
                'status': transaccion.status
            },
            status=status.HTTP_200_OK
        )