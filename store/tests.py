from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Categoria, Producto


class ProductoSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat_armazones = Categoria.objects.create(nombre='Armazones ópticos', slug='armazones-opticos')
        self.cat_sol = Categoria.objects.create(nombre='Lentes de sol', slug='lentes-de-sol')

        self.p1 = Producto.objects.create(
            categoria=self.cat_armazones,
            nombre='Armazón Titanio Classic',
            descripcion='Montura de aleación ligera y resistente.',
            sku='TIT-001',
            precio=Decimal('65000.00'),
            stock=10,
            color='Negro Mate',
            activo=True,
        )
        self.p2 = Producto.objects.create(
            categoria=self.cat_sol,
            nombre='Gafas Sol Polarizadas Aviador',
            descripcion='Protección UV400 categoría 3.',
            sku='SOL-AVI-02',
            precio=Decimal('45000.00'),
            stock=5,
            color='Dorado',
            activo=True,
        )
        self.p3 = Producto.objects.create(
            categoria=self.cat_armazones,
            nombre='Armazón Acetato Vintage',
            descripcion='Estilo retro carey.',
            sku='ACT-VIN-03',
            precio=Decimal('35000.00'),
            stock=0,
            color='Carey',
            activo=True,
        )

    def test_search_by_name(self):
        res = self.client.get('/api/store/productos/', {'search': 'Titanio'})
        self.assertEqual(res.status_code, 200)
        names = [p['nombre'] for p in res.data]
        self.assertIn('Armazón Titanio Classic', names)
        self.assertNotIn('Gafas Sol Polarizadas Aviador', names)

    def test_search_by_category_name(self):
        res = self.client.get('/api/store/productos/', {'search': 'sol'})
        self.assertEqual(res.status_code, 200)
        names = [p['nombre'] for p in res.data]
        self.assertIn('Gafas Sol Polarizadas Aviador', names)

    def test_search_by_sku(self):
        res = self.client.get('/api/store/productos/', {'search': 'TIT-001'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['sku'], 'TIT-001')

    def test_search_by_color(self):
        res = self.client.get('/api/store/productos/', {'search': 'Dorado'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['nombre'], 'Gafas Sol Polarizadas Aviador')

    def test_search_empty_result(self):
        res = self.client.get('/api/store/productos/', {'search': 'InexistenteXYZ123'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 0)

