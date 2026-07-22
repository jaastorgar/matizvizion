import logging
import uuid

from decouple import config
from django.db import transaction
from requests import RequestException
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import requests

from orders.models import HistorialEstado, Orden

from .models import LogPago, TransaccionWebpay
from .serializers import (
    TransaccionWebpaySerializer,
    WebpayCreateSerializer,
    WebpayReturnSerializer,
)


logger = logging.getLogger(__name__)


TBK_BASE = {
    'Integration': 'https://webpay3gint.transbank.cl',
    'TEST':        'https://webpay3gint.transbank.cl',
    'Production':  'https://webpay3g.transbank.cl',
}
TBK_PATH = '/rswebpaytransaction/api/webpay/v1.3/transactions'


def _tbk_base():
    env = config('WEBPAY_ENVIRONMENT', default='Integration')
    return TBK_BASE.get(env, TBK_BASE['Integration'])


def _tbk_headers():
    commerce_code = config('WEBPAY_COMMERCE_CODE', default='')
    api_key = config('WEBPAY_API_KEY', default='')
    if not commerce_code or not api_key:
        raise ValueError('WEBPAY_COMMERCE_CODE / WEBPAY_API_KEY no configurados.')
    return {
        'Tbk-Api-Key-Id': commerce_code,
        'Tbk-Api-Key-Secret': api_key,
        'Content-Type': 'application/json',
    }


def _tbk_create(buy_order, session_id, amount, return_url):
    resp = requests.post(
        _tbk_base() + TBK_PATH,
        headers=_tbk_headers(),
        json={
            'buy_order': buy_order,
            'session_id': session_id,
            'amount': amount,
            'return_url': return_url,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _tbk_commit(token_ws):
    resp = requests.put(
        _tbk_base() + TBK_PATH + '/' + token_ws,
        headers=_tbk_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _revertir_stock(orden):
    for item in orden.items.select_related('producto').all():
        item.producto.stock += item.cantidad
        item.producto.save(update_fields=['stock'])


class WebpayCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WebpayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        orden_id = serializer.validated_data['orden_id']

        try:
            orden = Orden.objects.get(id=orden_id, cliente=request.user, estado='PENDIENTE')
        except Orden.DoesNotExist:
            return Response({'error': 'Orden no encontrada o no está en estado PENDIENTE.'}, status=status.HTTP_404_NOT_FOUND)

        if orden.total <= 0:
            return Response({'error': 'La orden no tiene un monto válido para pagar.'}, status=status.HTTP_400_BAD_REQUEST)

        return_url = config('WEBPAY_RETURN_URL', default='')
        if not return_url:
            return Response({'error': 'WEBPAY_RETURN_URL no está configurada.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        buy_order = 'ORD-' + str(orden.id) + '-' + uuid.uuid4().hex[:8]
        session_id = 'SESS-' + str(request.user.id) + '-' + str(orden.id) + '-' + uuid.uuid4().hex[:8]
        amount = int(orden.total)

        try:
            data = _tbk_create(buy_order, session_id, amount, return_url)
        except (RequestException, ValueError) as error:
            logger.error('Error creando transacción Webpay: %s', error)
            return Response({'error': 'No se pudo iniciar la transacción en Transbank.'}, status=status.HTTP_502_BAD_GATEWAY)

        token = data.get('token')
        url = data.get('url')
        if not token or not url:
            logger.error('Respuesta inválida de Transbank: %s', data)
            return Response({'error': 'Respuesta inválida de Transbank.'}, status=status.HTTP_502_BAD_GATEWAY)

        transaccion = TransaccionWebpay.objects.create(
            orden=orden, buy_order=buy_order, session_id=session_id,
            token=token, amount=orden.total, status='INICIADA',
        )
        LogPago.objects.create(transaccion=transaccion, raw_response=data)

        return Response({
            'url': url,
            'token': token,
            'transaccion': TransaccionWebpaySerializer(transaccion).data,
        }, status=status.HTTP_201_CREATED)


class WebpayReturnView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data_in = request.data if request.data else request.query_params
        serializer = WebpayReturnSerializer(data=data_in)
        serializer.is_valid(raise_exception=True)
        token_ws = serializer.validated_data['token_ws']

        try:
            transaccion = TransaccionWebpay.objects.select_for_update().select_related('orden').get(token=token_ws)
        except TransaccionWebpay.DoesNotExist:
            return Response({'error': 'Transacción no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        orden = transaccion.orden

        if transaccion.status != 'INICIADA':
            return Response({'message': 'Transacción ya procesada previamente.', 'status': transaccion.status}, status=status.HTTP_200_OK)

        try:
            data = _tbk_commit(token_ws)
        except (RequestException, ValueError) as error:
            logger.error('Error confirmando pago Webpay: %s', error)
            LogPago.objects.create(transaccion=transaccion, raw_response={'error': str(error)})
            transaccion.status = 'ERROR'
            transaccion.save()
            return Response({'error': 'No se pudo confirmar el pago en Transbank.'}, status=status.HTTP_502_BAD_GATEWAY)

        LogPago.objects.create(transaccion=transaccion, raw_response=data)

        status_tbk = data.get('status')
        response_code = data.get('response_code')

        if status_tbk == 'AUTHORIZED' and response_code == 0:
            transaccion.status = 'AUTHORIZED'
            transaccion.save()
            if orden.estado == 'PENDIENTE':
                HistorialEstado.objects.create(orden=orden, estado_anterior=orden.estado, estado_nuevo='PAGADA')
                orden.estado = 'PAGADA'
                orden.save()
            return Response({'message': 'Pago exitoso.', 'orden_id': orden.id, 'status': 'AUTHORIZED'}, status=status.HTTP_200_OK)

        transaccion.status = status_tbk or 'RECHAZADA'
        transaccion.save()
        if orden.estado == 'PENDIENTE':
            HistorialEstado.objects.create(orden=orden, estado_anterior=orden.estado, estado_nuevo='FALLIDA')
            orden.estado = 'FALLIDA'
            orden.save()
            _revertir_stock(orden)

        return Response({'message': 'Pago rechazado o fallido.', 'orden_id': orden.id, 'status': transaccion.status}, status=status.HTTP_200_OK)