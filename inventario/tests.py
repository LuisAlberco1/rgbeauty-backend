import json
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import RequestFactory, SimpleTestCase

from .management.commands.link_stock_user import Command
from .models import Inventario, Producto
from .services import MovimientoStockError, calcular_stock_nuevo
from .views import stock_actual


class VincularUsuarioStockTests(SimpleTestCase):
    @patch("builtins.input", return_value="  12345678-9  ")
    def test_solicita_valor_y_elimina_espacios(self, input_mock):
        command = Command()

        self.assertEqual(command._read_value("RUT"), "12345678-9")
        input_mock.assert_called_once_with("RUT: ")

    @patch("builtins.input", return_value="")
    def test_rechaza_valor_obligatorio_vacio(self, _input_mock):
        with self.assertRaises(CommandError):
            Command()._read_value("RUT")


class StockActualEndpointTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_devuelve_stock_actual_para_usuario_autenticado(self):
        request = self.request_factory.get(
            "/stock/actual/",
            {"inventario": "2", "producto": "7"},
        )
        request.user = SimpleNamespace(is_authenticated=True)

        with (
            patch("inventario.views.Inventario") as inventario_model,
            patch("inventario.views.Producto") as producto_model,
            patch("inventario.views.connection") as db_connection,
        ):
            inventario_model.DoesNotExist = Inventario.DoesNotExist
            producto_model.DoesNotExist = Producto.DoesNotExist
            cursor = db_connection.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (12,)

            response = stock_actual(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, '{"stock": 12}')
        inventario_model.objects.only.return_value.get.assert_called_once_with(pk=2, activo=True)
        producto_model.objects.only.return_value.get.assert_called_once_with(pk=7, activo=True)

    def test_rechaza_ids_invalidos(self):
        request = self.request_factory.get(
            "/stock/actual/",
            {"inventario": "abc", "producto": "7"},
        )
        request.user = SimpleNamespace(is_authenticated=True)

        response = stock_actual(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", json.loads(response.content))


class CalculoStockTests(SimpleTestCase):
    def test_entrada_incrementa_stock(self):
        self.assertEqual(calcular_stock_nuevo("Entrada", 5, 3), 8)

    def test_salida_disminuye_stock(self):
        self.assertEqual(calcular_stock_nuevo("Salida", 2, 5), 3)

    def test_salida_no_permite_stock_negativo(self):
        with self.assertRaises(MovimientoStockError):
            calcular_stock_nuevo("Salida", 4, 3)

    def test_ajuste_usa_el_conteo_fisico_final(self):
        self.assertEqual(calcular_stock_nuevo("Ajuste", 2, 5), 2)

    def test_ajuste_puede_dejar_stock_en_cero(self):
        self.assertEqual(calcular_stock_nuevo("Ajuste", 0, 5), 0)

    def test_movimiento_no_acepta_cantidades_invalidas(self):
        for tipo, cantidad in (("Entrada", 0), ("Salida", 0), ("Ajuste", -1)):
            with self.subTest(tipo=tipo, cantidad=cantidad):
                with self.assertRaises(MovimientoStockError):
                    calcular_stock_nuevo(tipo, cantidad, 4)

    def test_entrada_no_supera_el_limite_de_stock(self):
        with self.assertRaises(MovimientoStockError):
            calcular_stock_nuevo("Entrada", 1, 2_147_483_647)
