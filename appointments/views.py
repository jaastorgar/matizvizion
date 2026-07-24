from datetime import date

from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Tecnologo, BloqueHorario, CitaMedica
from .serializers import TecnologoSerializer, BloqueHorarioSerializer, CitaMedicaSerializer


class TecnologoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tecnologo.objects.select_related('sucursal').all()
    serializer_class = TecnologoSerializer
    permission_classes = [AllowAny]


class BloqueHorarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BloqueHorarioSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = BloqueHorario.objects.filter(disponible=True, fecha__gte=date.today()).select_related('tecnologo__sucursal')
        s = self.request.query_params.get('sucursal')
        f = self.request.query_params.get('fecha')
        if s:
            qs = qs.filter(tecnologo__sucursal_id=s)
        if f:
            qs = qs.filter(fecha=f)
        return qs


class CitaMedicaViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CitaMedicaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal')
        if self.request.user.role == 'CLIENTE':
            return qs.filter(cliente=self.request.user)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bloque_id = serializer.validated_data['bloque'].id
        try:
            bloque = BloqueHorario.objects.select_for_update().select_related('tecnologo__sucursal').get(id=bloque_id, disponible=True)
        except BloqueHorario.DoesNotExist:
            return Response({'error': 'El bloque seleccionado ya no esta disponible.'}, status=status.HTTP_400_BAD_REQUEST)
        if bloque.fecha < date.today():
            return Response({'error': 'No se puede agendar en una fecha pasada.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cita = CitaMedica.objects.create(cliente=request.user, bloque=bloque, estado='AGENDADA')
        except IntegrityError:
            return Response({'error': 'Este bloque ya fue reservado por otro paciente.'}, status=status.HTTP_400_BAD_REQUEST)
        bloque.disponible = False
        bloque.save(update_fields=['disponible'])
        cita = CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal').get(pk=cita.pk)
        return Response(self.get_serializer(cita).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        if request.user.role == 'CLIENTE' and cita.cliente_id != request.user.id:
            return Response({'error': 'No puedes cancelar una cita que no es tuya.'}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            cita = CitaMedica.objects.select_for_update().select_related('bloque').get(pk=cita.pk)
            if cita.estado == 'CANCELADA':
                return Response(self.get_serializer(cita).data)
            if cita.estado in ('COMPLETADA', 'NO_ASISTIO'):
                return Response({'error': 'No se puede cancelar una cita ya atendida.'}, status=status.HTTP_400_BAD_REQUEST)
            cita.estado = 'CANCELADA'
            cita.save(update_fields=['estado'])
            b = cita.bloque
            b.disponible = True
            b.save(update_fields=['disponible'])
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=['post'], url_path='reagendar')
    def reagendar(self, request, pk=None):
        """Traslada la MISMA cita a un bloque nuevo de forma atomica: libera el
        viejo y reserva el nuevo. Si el nuevo ya no esta libre -> rollback y el
        turno actual NO se pierde. NO crea una cita nueva ni borra la vieja."""
        nuevo_id = request.data.get('bloque')
        if not nuevo_id:
            return Response({'error': 'Debes indicar el nuevo bloque.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            cita = CitaMedica.objects.select_for_update().select_related('bloque').get(pk=pk)
            if request.user.role == 'CLIENTE' and cita.cliente_id != request.user.id:
                return Response({'error': 'No puedes reagendar una cita que no es tuya.'}, status=status.HTTP_403_FORBIDDEN)
            if cita.estado not in ('AGENDADA', 'CONFIRMADA'):
                return Response({'error': 'Solo se puede reagendar una cita agendada.'}, status=status.HTTP_400_BAD_REQUEST)
            viejo = cita.bloque
            if str(viejo.id) == str(nuevo_id):
                return Response(self.get_serializer(cita).data)
            try:
                nuevo = BloqueHorario.objects.select_for_update().select_related('tecnologo__sucursal').get(pk=nuevo_id, disponible=True)
            except BloqueHorario.DoesNotExist:
                return Response({'error': 'El nuevo bloque ya no esta disponible.'}, status=status.HTTP_400_BAD_REQUEST)
            if nuevo.fecha < date.today():
                return Response({'error': 'No se puede reagendar a una fecha pasada.'}, status=status.HTTP_400_BAD_REQUEST)
            viejo.disponible = True
            viejo.save(update_fields=['disponible'])
            cita.bloque = nuevo
            cita.estado = 'AGENDADA'
            cita.save(update_fields=['bloque', 'estado'])
            nuevo.disponible = False
            nuevo.save(update_fields=['disponible'])
        cita = CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal').get(pk=pk)
        from django.db import transaction as _tx
        from core.notifications import notify_cita
        cid = cita.pk
        _tx.on_commit(lambda: notify_cita(
            CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal').get(pk=cid), 'reagendada'))
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=['patch'], url_path='marcar')
    def marcar(self, request, pk=None):
        if request.user.role not in ('VENDEDOR', 'ADMIN'):
            return Response({'error': 'Solo vendedores o administradores.'}, status=status.HTTP_403_FORBIDDEN)
        nuevo = request.data.get('estado')
        if nuevo not in ('COMPLETADA', 'NO_ASISTIO', 'CANCELADA'):
            return Response({'error': 'Estado invalido.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            cita = CitaMedica.objects.select_for_update().select_related('bloque').get(pk=pk)
            if cita.estado == nuevo:
                return Response(self.get_serializer(cita).data)
            if cita.estado in ('COMPLETADA', 'NO_ASISTIO') and nuevo == 'CANCELADA':
                return Response({'error': 'No se puede cancelar una cita ya atendida.'}, status=status.HTTP_400_BAD_REQUEST)
            cita.estado = nuevo
            cita.save(update_fields=['estado'])
            if nuevo == 'CANCELADA':
                b = cita.bloque
                b.disponible = True
                b.save(update_fields=['disponible'])
        cita = CitaMedica.objects.select_related('cliente', 'bloque__tecnologo__sucursal').get(pk=pk)
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=['post'], url_path='completar')
    def completar(self, request, pk=None):
        if request.user.role not in ('VENDEDOR', 'ADMIN'):
            return Response({'error': 'Solo vendedores o administradores.'}, status=status.HTTP_403_FORBIDDEN)
        cita = self.get_object()
        if cita.estado == 'CANCELADA':
            return Response({'error': 'No se puede completar una cita cancelada.'}, status=status.HTTP_400_BAD_REQUEST)
        cita.estado = 'COMPLETADA'
        cita.save(update_fields=['estado'])
        return Response(self.get_serializer(cita).data)