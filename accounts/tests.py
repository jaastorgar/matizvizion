from datetime import timedelta
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import ConsentimientoLog, CustomUser, PerfilCliente, SolicitudSupresion
from orders.models import Carrito, Orden


class LeyProteccionDatosTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='test.paciente@ejemplo.cl',
            password='TestPassword123!',
            first_name='Juan',
            last_name='Perez',
            telefono='+56911223344',
            direccion='Av. Providencia 1234',
            comuna='Providencia',
            region='Metropolitana'
        )
        self.perfil = PerfilCliente.objects.create(
            user=self.user,
            rut='12345678-5',
            telefono='+56911223344',
            direccion='Av. Providencia 1234',
            comuna='Providencia',
            region='Metropolitana'
        )

    def test_consentimiento_audit_log(self):
        """Auditoría de consentimientos (Ley 21.719 / Principio de Responsabilidad)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('consentimientos')

        # Otorgar consentimiento de salud
        resp = self.client.patch(url, {'consiente_salud': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['consiente_salud'])

        log_salud = ConsentimientoLog.objects.filter(
            usuario=self.user,
            tipo=ConsentimientoLog.Tipo.SALUD,
            accion=ConsentimientoLog.Accion.OTORGADO
        ).first()
        self.assertIsNotNone(log_salud)
        self.assertEqual(log_salud.email_snapshot, 'test.paciente@ejemplo.cl')

        # Revocar consentimiento de salud
        resp = self.client.patch(url, {'consiente_salud': False}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['consiente_salud'])

        log_revocado = ConsentimientoLog.objects.filter(
            usuario=self.user,
            tipo=ConsentimientoLog.Tipo.SALUD,
            accion=ConsentimientoLog.Accion.REVOCADO
        ).first()
        self.assertIsNotNone(log_revocado)

        # Modificar marketing
        resp = self.client.patch(url, {'consiente_marketing': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        log_mkt = ConsentimientoLog.objects.filter(
            usuario=self.user,
            tipo=ConsentimientoLog.Tipo.MARKETING,
            accion=ConsentimientoLog.Accion.OTORGADO
        ).first()
        self.assertIsNotNone(log_mkt)

    def test_exportar_datos_portabilidad(self):
        """Derecho de portabilidad (Ley 21.719): exportación en JSON estructurado."""
        self.client.force_authenticate(user=self.user)
        url = reverse('exportar_datos')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('perfil', resp.data)
        self.assertIn('consentimientos', resp.data)
        self.assertIn('historial_auditoria_consentimientos', resp.data)
        self.assertEqual(resp.data['perfil']['email'], 'test.paciente@ejemplo.cl')
        self.assertEqual(resp.data['perfil']['rut'], '123456785')

    def test_solicitud_supresion_bloqueada_con_pedidos_activos(self):
        """Supresión bloqueada si hay compras en tránsito."""
        Orden.objects.create(
            cliente=self.user,
            total=45000,
            estado=Orden.Estado.EN_PREPARACION,
            modo_pago='COMPLETO'
        )
        self.client.force_authenticate(user=self.user)
        url = reverse('solicitar_supresion')
        resp = self.client.post(url, {'motivo': 'Quiero borrar mi cuenta'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pedidos en proceso', resp.data['detail'])

    def test_solicitud_supresion_exitosa_con_resguardo_legal(self):
        """Supresión exitosa: desactiva, anonimiza y crea auditoría formal."""
        self.client.force_authenticate(user=self.user)
        url = reverse('solicitar_supresion')
        resp = self.client.post(url, {'motivo': 'Baja voluntaria'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['ok'])

        # Recargar usuario
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.first_name, 'Usuario')
        self.assertEqual(self.user.last_name, 'Anonimizado')
        self.assertEqual(self.user.telefono, '')
        self.assertTrue(self.user.email.startswith('suprimido_'))

        # Perfil anonimizado
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, '')
        self.assertEqual(self.perfil.direccion, '')

        # Auditoría formal
        solicitud = SolicitudSupresion.objects.filter(email_original='test.paciente@ejemplo.cl').first()
        self.assertIsNotNone(solicitud)
        self.assertEqual(solicitud.motivo, 'Baja voluntaria')

    def test_purge_abandoned_guests_command(self):
        """Limitación del plazo de conservación: purga de invitados inactivos."""
        # Invitado viejo abandonado (90 días atrás, sin compras)
        antiguo = CustomUser.objects.create_guest(email='viejo.invitado@test.cl')
        antiguo.date_joined = timezone.now() - timedelta(days=90)
        antiguo.save()
        c_antiguo = Carrito.objects.create(cliente=antiguo)

        # Invitado reciente (5 días atrás)
        reciente = CustomUser.objects.create_guest(email='nuevo.invitado@test.cl')
        reciente.date_joined = timezone.now() - timedelta(days=5)
        reciente.save()

        # Ejecutar simulación dry-run
        call_command('purge_abandoned_guests', days=60, dry_run=True)
        self.assertTrue(CustomUser.objects.filter(pk=antiguo.pk).exists())

        # Ejecutar purga real
        call_command('purge_abandoned_guests', days=60)
        self.assertFalse(CustomUser.objects.filter(pk=antiguo.pk).exists())
        self.assertTrue(CustomUser.objects.filter(pk=reciente.pk).exists())
        self.assertFalse(Carrito.objects.filter(pk=c_antiguo.pk).exists())
