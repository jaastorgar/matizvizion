from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from store.models import Categoria, Producto
from orders.models import EstadoOrden, ItemOrden, Orden, ResolucionDevolucion, SolicitudDevolucion

User = get_user_model()


class StockAutomaticoRestorationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@matizvision.cl',
            password='Password123!',
            role='CLIENTE'
        )
        self.categoria = Categoria.objects.create(nombre='Armazones')
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            nombre='Armazón Titanio',
            sku='ARM-TIT-01',
            precio=Decimal('50000.00'),
            stock=10,
        )

    def _crear_orden(self, cantidad=2, estado=EstadoOrden.PENDIENTE):
        # Descuenta stock como lo hace el checkout real
        self.producto.stock -= cantidad
        self.producto.save(update_fields=['stock'])

        orden = Orden.objects.create(
            cliente=self.user,
            total=Decimal('50000.00') * cantidad,
            estado=estado,
        )
        ItemOrden.objects.create(
            orden=orden,
            producto=self.producto,
            precio_unitario=Decimal('50000.00'),
            cantidad=cantidad,
        )
        return orden

    def test_cancelacion_via_cambiar_estado_repone_stock(self):
        orden = self._crear_orden(cantidad=3)
        self.assertEqual(self.producto.stock, 7)
        self.assertFalse(orden.stock_revertido)

        orden.cambiar_estado(EstadoOrden.CANCELADA)
        orden.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertTrue(orden.stock_revertido)
        self.assertEqual(self.producto.stock, 10)

    def test_cancelacion_via_save_directo_repone_stock(self):
        # Simula cambio directo en Django Admin dropdown
        orden = self._crear_orden(cantidad=2)
        self.assertEqual(self.producto.stock, 8)

        orden.estado = EstadoOrden.CANCELADA
        orden.save()
        orden.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertTrue(orden.stock_revertido)
        self.assertEqual(self.producto.stock, 10)

    def test_fallida_repone_stock(self):
        # Simula fallo en Webpay / pasarela de pagos
        orden = self._crear_orden(cantidad=4)
        self.assertEqual(self.producto.stock, 6)

        orden.cambiar_estado(EstadoOrden.FALLIDA)
        orden.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertTrue(orden.stock_revertido)
        self.assertEqual(self.producto.stock, 10)

    def test_devolucion_directa_repone_stock(self):
        # Orden entregada que el admin/vendedor pasa a DEVUELTA
        orden = self._crear_orden(cantidad=2, estado=EstadoOrden.ENTREGADA)
        self.assertEqual(self.producto.stock, 8)

        orden.cambiar_estado(EstadoOrden.DEVUELTA)
        orden.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertTrue(orden.stock_revertido)
        self.assertEqual(self.producto.stock, 10)

    def test_idempotencia_revertir_stock(self):
        # Múltiples ejecuciones nunca deben duplicar stock
        orden = self._crear_orden(cantidad=3)
        self.assertEqual(self.producto.stock, 7)

        unidades_1 = orden.revertir_stock()
        self.assertEqual(unidades_1, 3)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

        # Segunda llamada directa no debe añadir nada
        unidades_2 = orden.revertir_stock()
        self.assertEqual(unidades_2, 0)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

        # Tercera llamada vía save tampoco
        orden.save()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_solicitud_devolucion_parcial_y_total_sin_duplicar(self):
        # Orden con 2 unidades
        orden = self._crear_orden(cantidad=2, estado=EstadoOrden.ENTREGADA)
        item = orden.items.first()
        self.assertEqual(self.producto.stock, 8)

        # 1. Devolución de 1 unidad
        sol1 = SolicitudDevolucion.objects.create(
            orden=orden,
            cliente=self.user,
            motivo='No me gustó el color',
            cantidades={str(item.id): 1},
        )
        sol1.items.add(item)
        sol1.revertir_stock_items()
        sol1.estado = 'APROBADA'
        sol1.resolucion = ResolucionDevolucion.DEVOLUCION
        sol1.save()

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 9)  # 8 + 1 = 9

        # 2. Devolución de la 2da unidad restante
        sol2 = SolicitudDevolucion.objects.create(
            orden=orden,
            cliente=self.user,
            motivo='Devolución del resto',
            cantidades={str(item.id): 1},
        )
        sol2.items.add(item)
        sol2.revertir_stock_items()
        sol2.estado = 'APROBADA'
        sol2.resolucion = ResolucionDevolucion.DEVOLUCION
        sol2.save()

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)  # 9 + 1 = 10

        # Ahora la orden pasa formalmente a DEVUELTA
        orden.cambiar_estado(EstadoOrden.DEVUELTA)
        orden.refresh_from_db()
        self.producto.refresh_from_db()

        # El stock NO se debe haber incrementado de nuevo (debe mantenerse en 10)
        self.assertEqual(self.producto.stock, 10)
        self.assertTrue(orden.stock_revertido)

    def test_eliminacion_de_orden_activa_restituye_stock(self):
        # Si una orden activa es borrada, su stock reservado debe ser restituido
        orden = self._crear_orden(cantidad=2, estado=EstadoOrden.PAGADA)
        self.assertEqual(self.producto.stock, 8)

        orden.delete()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
