from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsClienteUser, IsVendedorUser

from .models import BloqueHorario, CitaMedica, EstadoCita, Tecnologo
from .serializers import (
    BloqueHorarioSerializer,
    CitaMedicaSerializer,
    TecnologoSerializer,
)


class TecnologoViewSet(viewsets.ReadOnlyModelViewSet):
    """Listado público de tecnólogos activos."""
    queryset = Tecnologo.objects.filter(activo=True).select_related('sucursal')
    serializer_class = TecnologoSerializer
    permission_classes = [AllowAny]


class BloqueHorarioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado público de bloques disponibles.
    Filtros opcionales: ?sucursal=<id> &fecha=YYYY-MM-DD
    Por defecto solo muestra bloques de hoy en adelante.
    """
    serializer_class = BloqueHorarioSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = BloqueHorario.objects.filter(
            disponible=True,
            fecha__gte=date.today(),
            tecnologo__activo=True,
        ).select_related('tecnologo__sucursal')

        sucursal_id = self.request.query_params.get('sucursal')
        fecha = self.request.query_params.get('fecha')

        if sucursal_id:
            queryset = queryset.filter(tecnologo__sucursal_id=sucursal_id)
        if fecha:
            queryset = queryset.filter(fecha=fecha)

        return queryset


class CitaMedicaViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    - CLIENTE: crea citas, ve las suyas y puede cancelarlas.
    - VENDEDOR/ADMIN: ve todas y puede completar/cancelar.
    No expone PUT/PATCH/DELETE genéricos (el estado no se edita a mano).
    """
    serializer_class = CitaMedicaSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsClienteUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = CitaMedica.objects.select_related(
            'cliente',
            'bloque__tecnologo__sucursal',
        )
        if self.request.user.role == 'CLIENTE':
            return queryset.filter(cliente=self.request.user)
        return queryset  # VENDEDOR / ADMIN ven todas

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bloque_id = serializer.validated_data['bloque'].id

        try:
            # Bloqueo de fila para evitar doble reserva (condición de carrera)
            bloque = BloqueHorario.objects.select_for_update().select_related(
                'tecnologo__sucursal'
            ).get(id=bloque_id, disponible=True)
        except BloqueHorario.DoesNotExist:
            return Response(
                {'error': 'El bloque seleccionado ya no está disponible.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if bloque.fecha < date.today():
            return Response(
                {'error': 'No se puede agendar en una fecha pasada.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cita = CitaMedica.objects.create(
                cliente=request.user,
                bloque=bloque,
                estado=EstadoCita.AGENDADA,
            )
        except IntegrityError:
            return Response(
                {'error': 'Este bloque ya fue reservado por otro paciente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Marcar el bloque como ocupado
        bloque.disponible = False
        bloque.save(update_fields=['disponible'])

        # Recargar con relaciones para serializar completo
        cita = CitaMedica.objects.select_related(
            'cliente', 'bloque__tecnologo__sucursal'
        ).get(pk=cita.pk)

        return Response(
            CitaMedicaSerializer(cita).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """
        Cancela la cita y libera el bloque.
        CLIENTE solo puede cancelar la suya; VENDEDOR/ADMIN cualquiera.
        """
        cita = self.get_object()

        if request.user.role == 'CLIENTE' and cita.cliente_id != request.user.id:
            return Response(
                {'error': 'No puedes cancelar una cita que no es tuya.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():
                cita = CitaMedica.objects.select_for_update().select_related('bloque').get(pk=cita.pk)
                cita.cancelar()
        except ValidationError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(cita).data)

    @action(
        detail=True,
        methods=['post'],
        url_path='completar',
        permission_classes=[IsAuthenticated, IsVendedorUser],
    )
    def completar(self, request, pk=None):
        """Solo VENDEDOR/ADMIN: marca la cita como COMPLETADA (no libera el bloque)."""
        cita = self.get_object()

        if cita.estado == EstadoCita.CANCELADA:
            return Response(
                {'error': 'No se puede completar una cita cancelada.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cita.estado = EstadoCita.COMPLETADA
        cita.save(update_fields=['estado'])

        return Response(self.get_serializer(cita).data)