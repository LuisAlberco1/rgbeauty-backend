import json
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management.base import CommandError
from django.core.exceptions import PermissionDenied
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .management.commands.link_stock_user import Command
from .management.commands.setup_inventory_permissions import (
    GROUP_NAME,
    Command as SetupInventoryPermissionsCommand,
)
from .forms import HistorialFiltroForm
from .models import (
    CategoriaProducto,
    Inventario,
    Marca,
    MovimientoInventario,
    Persona,
    Producto,
    ProductoPrecio,
    Stock,
    TipoMovimiento,
    DetalleMovimiento,
    UsuarioNegocio,
)
from .services import (
    MovimientoStockError,
    calcular_stock_nuevo,
    clasificar_stock,
    registrar_movimiento_stock,
)
from .admin import UsuarioNegocioAdmin
from .views import (
    _puede_editar_producto,
    _verificar_permiso_producto,
)


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


class SetupInventoryPermissionsTests(TestCase):
    def test_creates_group_and_assigns_product_change_permission_idempotently(self):
        content_type = ContentType.objects.get(
            app_label="inventario",
            model="producto",
        )
        permission = Permission.objects.get(
            content_type=content_type,
            codename="change_producto",
        )
        command = SetupInventoryPermissionsCommand()

        command.handle()
        command.handle()

        group = Group.objects.get(name=GROUP_NAME)
        self.assertEqual(Group.objects.filter(name=GROUP_NAME).count(), 1)
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())


class InventarioAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="inventory-admin",
            email="admin@example.com",
            password="StrongPass#1234",
        )

    def test_inventory_models_are_registered_in_admin(self):
        models = (
            CategoriaProducto,
            Inventario,
            Marca,
            Producto,
            ProductoPrecio,
            Stock,
            TipoMovimiento,
            Persona,
            UsuarioNegocio,
            MovimientoInventario,
            DetalleMovimiento,
        )
        for model in models:
            self.assertTrue(admin.site.is_registered(model), model.__name__)

        self.client.force_login(self.admin_user)
        for model in models:
            response = self.client.get(
                f"/admin/inventario/{model._meta.model_name}/"
            )
            self.assertEqual(response.status_code, 200, model.__name__)
        self.assertEqual(
            self.client.get("/admin/inventario/producto/add/").status_code,
            200,
        )

    def test_stock_admin_is_read_only(self):
        model_admin = admin.site._registry[Stock]
        request = RequestFactory().get("/admin/inventario/stock/")
        request.user = self.admin_user

        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_business_user_admin_requires_existing_django_account(self):
        person = Persona.objects.create(
            rut="22222222-2",
            nombre="Asistente",
            apellido_paterno="Inventario",
            email="asistente@example.com",
        )
        user_model = get_user_model()
        user_model.objects.create_user(
            username="assistant-account",
            password="StrongPass#1234",
        )

        valid_form = UsuarioNegocioAdmin.Form(data={
            "persona": person.pk,
            "nombre_usuario": "assistant-account",
            "activo": "on",
        })
        invalid_form = UsuarioNegocioAdmin.Form(data={
            "persona": person.pk,
            "nombre_usuario": "missing-account",
            "activo": "on",
        })

        self.assertTrue(valid_form.is_valid(), valid_form.errors)
        self.assertFalse(invalid_form.is_valid())
        self.assertIn("Crea primero esta cuenta", str(invalid_form.errors))


class AccesoPrivadoTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_public_registration_is_unavailable(self):
        response = self.client.post("/registro/", {
            "username": "unauthorized-user",
            "password1": "StrongPass#1234",
            "password2": "StrongPass#1234",
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.user_model.objects.filter(username="unauthorized-user").exists())

    def test_login_works_and_logout_requires_post(self):
        self.user_model.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="StrongPass#1234",
        )

        response = self.client.post("/login/", {
            "username": "login-user",
            "password": "StrongPass#1234",
        })
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertEqual(self.client.post("/logout/").status_code, 302)

    def test_login_page_has_no_public_registration_link(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="/registro/"')
        self.assertNotContains(response, "Catálogo de productos")
        self.assertNotContains(response, "Cerrar sesión")


class CuentaUsuarioTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="staff-user",
            first_name="Nombre",
            last_name="Apellido",
            email="staff@example.com",
            password="StrongPass#1234",
        )
        self.client.force_login(self.user)

    def test_account_redirects_anonymous_users_to_login(self):
        self.client.logout()

        response = self.client.get("/cuenta/")

        self.assertRedirects(response, "/login/?next=/cuenta/")

    def test_account_shows_user_data_and_is_protected(self):
        category = CategoriaProducto.objects.create(nombre="Cuidado")
        brand = Marca.objects.create(nombre="Marca demo")
        Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="STAFF-001",
            nombre="Producto personal",
            creado_por=self.user,
        )

        response = self.client.get("/cuenta/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "staff-user")
        self.assertContains(response, "staff@example.com")
        self.assertContains(response, "Productos registrados por ti")
        self.assertContains(response, ">1</strong>")
        self.assertContains(response, "Mi cuenta")
        self.assertContains(response, "Cerrar sesión")

    def test_profile_updates_email_and_name_and_shows_success_message(self):
        response = self.client.post("/cuenta/", {
            "first_name": "Nuevo",
            "last_name": "Nombre",
            "email": " STAFF@EXAMPLE.COM ",
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Nuevo")
        self.assertEqual(self.user.last_name, "Nombre")
        self.assertEqual(self.user.email, "staff@example.com")
        self.assertContains(response, "Los datos de tu cuenta se actualizaron correctamente.")

    def test_profile_rejects_email_used_by_another_user(self):
        self.user_model.objects.create_user(
            username="another-staff",
            email="taken@example.com",
            password="StrongPass#5678",
        )

        response = self.client.post("/cuenta/", {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "TAKEN@example.com",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este correo ya está en uso.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "staff@example.com")

    def test_password_change_keeps_user_logged_in(self):
        response = self.client.post("/cuenta/contrasena/", {
            "old_password": "StrongPass#1234",
            "new_password1": "NewStrongPass#1234",
            "new_password2": "NewStrongPass#1234",
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass#1234"))
        self.assertContains(response, "Tu contraseña se actualizó correctamente.")
        self.assertEqual(self.client.get("/cuenta/").status_code, 200)


class ProductosPaginacionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="catalog-user",
            password="StrongPass#1234",
        )
        self.category = CategoriaProducto.objects.create(nombre="Cuidado")
        self.brand = Marca.objects.create(nombre="Marca demo")
        for index in range(11):
            Producto.objects.create(
                categoria=self.category,
                marca=self.brand,
                sku=f"DEMO-{index:03d}",
                nombre=f"Producto demo {index:02d}",
            )
        self.client.force_login(self.user)

    def test_catalog_paginates_ten_products_per_page(self):
        response = self.client.get("/productos/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
        self.assertContains(response, "Página 1 de 2")
        self.assertContains(response, "page=2")

    def test_filters_are_preserved_while_changing_page(self):
        query = (
            f"?buscar=Producto&categoria={self.category.pk}"
            f"&marca={self.brand.pk}&estado=activo&page=2"
        )
        response = self.client.get(f"/productos/{query}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertContains(response, "buscar=Producto")
        self.assertContains(response, f"categoria={self.category.pk}")
        self.assertContains(response, f"marca={self.brand.pk}")
        self.assertContains(response, "estado=activo")
        self.assertNotContains(response, "page=2&amp;page=")


class ProductoDetalleTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="product-owner",
            password="OwnerPass#1234",
        )
        self.other_user = self.user_model.objects.create_user(
            username="product-viewer",
            password="ViewerPass#1234",
        )
        category = CategoriaProducto.objects.create(nombre="Cuidado")
        brand = Marca.objects.create(nombre="Marca demo")
        self.product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="DEMO-001",
            nombre="Producto de prueba",
            descripcion="Descripción de prueba.",
            creado_por=self.owner,
        )
        ProductoPrecio.objects.create(
            producto=self.product,
            precio="12990.00",
            activo=True,
        )

    def test_detail_shows_product_relations_current_price_and_edit_action_for_owner(self):
        self.client.force_login(self.owner)

        response = self.client.get(f"/productos/{self.product.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Producto de prueba")
        self.assertContains(response, "DEMO-001")
        self.assertContains(response, "Cuidado")
        self.assertContains(response, "Marca demo")
        self.assertContains(response, "$12990,00")
        self.assertContains(response, "Editar producto")

    def test_other_authenticated_user_can_view_but_not_edit_product(self):
        self.client.force_login(self.other_user)

        response = self.client.get(f"/productos/{self.product.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Producto de prueba")
        self.assertNotContains(response, "Editar producto")

    def test_missing_product_returns_404(self):
        self.client.force_login(self.owner)

        response = self.client.get("/productos/999999/")

        self.assertEqual(response.status_code, 404)


class StockActualEndpointTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="stock-viewer",
            password="StrongPass#1234",
        )
        self.inventory = Inventario.objects.create(nombre="Bodega test")
        category = CategoriaProducto.objects.create(nombre="Stock test")
        brand = Marca.objects.create(nombre="Marca stock")
        self.product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="STOCK-001",
            nombre="Producto stock",
        )
        self.stock = Stock.objects.get(
            inventario=self.inventory,
            producto=self.product,
        )
        self.client.force_login(self.user)

    def test_devuelve_stock_actual_para_usuario_autenticado(self):
        self.stock.cantidad_actual = 12
        self.stock.save()
        response = self.client.get("/stock/actual/", {
            "inventario": self.inventory.pk,
            "producto": self.product.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, '{"stock": 12}')

    def test_rechaza_ids_invalidos(self):
        response = self.client.get("/stock/actual/", {
            "inventario": "abc",
            "producto": self.product.pk,
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", json.loads(response.content))


class DashboardStockTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="dashboard-viewer",
            password="StrongPass#1234",
        )
        inventory = Inventario.objects.create(nombre="Bodega dashboard")
        category = CategoriaProducto.objects.create(nombre="Dashboard")
        brand = Marca.objects.create(nombre="Marca dashboard")
        self.products = [
            Producto.objects.create(
                categoria=category,
                marca=brand,
                sku=f"DASH-{index:03d}",
                nombre=f"Producto dashboard {index}",
            )
            for index in range(2)
        ]
        Stock.objects.filter(
            inventario=inventory,
            producto=self.products[0],
        ).update(cantidad_actual=5)
        self.client.force_login(self.user)

    def test_dashboard_indicators_and_alerts_use_stock_records(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["productos_activos"], 2)
        self.assertEqual(response.context["unidades_stock"], 5)
        self.assertEqual(response.context["productos_stock_bajo"], 1)
        self.assertEqual(response.context["productos_agotados"], 1)
        self.assertEqual(len(response.context["alertas_stock"]), 2)


class ExistenciasFiltroTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="stock-filter",
            password="StrongPass#1234",
        )
        self.inventory = Inventario.objects.create(nombre="Bodega filtro")
        category = CategoriaProducto.objects.create(nombre="Filtro")
        brand = Marca.objects.create(nombre="Marca filtro")
        self.product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="FILTER-001",
            nombre="Producto filtrado",
        )
        Stock.objects.filter(
            inventario=self.inventory,
            producto=self.product,
        ).update(cantidad_actual=3)
        self.client.force_login(self.user)

    def test_filter_by_search_inventory_and_stock_state(self):
        response = self.client.get("/stock/", {
            "buscar": "FILTER",
            "inventario": self.inventory.pk,
            "estado": "bajo",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["stock_rows"]), 1)
        self.assertEqual(response.context["stock_rows"][0].cantidad_actual, 3)

    def test_search_does_not_treat_input_as_sql(self):
        response = self.client.get("/stock/", {
            "buscar": "' OR 1=1 --",
            "inventario": self.inventory.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stock_rows"], [])


class RegistrarMovimientoORMTests(TestCase):
    def setUp(self):
        self.inventory = Inventario.objects.create(nombre="Bodega movimiento")
        category = CategoriaProducto.objects.create(nombre="Movimiento")
        brand = Marca.objects.create(nombre="Marca movimiento")
        self.product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="MOV-001",
            nombre="Producto movimiento",
        )
        person = Persona.objects.create(
            rut="11111111-1",
            nombre="Admin",
            apellido_paterno="Inventario",
            email="admin-movimiento@example.com",
        )
        self.business_user = UsuarioNegocio.objects.create(
            persona=person,
            nombre_usuario="movement-user",
            password_hash="unused",
        )
        TipoMovimiento.objects.create(nombre="Entrada")
        TipoMovimiento.objects.create(nombre="Salida")

    def test_movement_updates_stock_and_records_audit_using_orm(self):
        result = registrar_movimiento_stock(
            inventario_id=self.inventory.pk,
            producto_id=self.product.pk,
            tipo="Entrada",
            cantidad=7,
            motivo="Reposición",
            observacion="Compra recibida",
            nombre_usuario=self.business_user.nombre_usuario,
        )

        stock = Stock.objects.get(
            inventario=self.inventory,
            producto=self.product,
        )
        self.assertEqual(stock.cantidad_actual, 7)
        self.assertIsNotNone(result.movimiento)
        self.assertEqual(result.stock_anterior, 0)
        self.assertEqual(result.stock_nuevo, 7)
        self.assertEqual(result.movimiento.detalles.get().cantidad, 7)


class PermisosProductoTests(SimpleTestCase):
    def setUp(self):
        self.owner = SimpleNamespace(
            pk=11,
            is_superuser=False,
            has_perm=lambda _permission: False,
        )
        self.other_user = SimpleNamespace(
            pk=12,
            is_superuser=False,
            has_perm=lambda _permission: False,
        )
        self.authorized_staff = SimpleNamespace(
            pk=13,
            is_superuser=False,
            has_perm=lambda permission: permission == "inventario.change_producto",
        )
        self.superuser = SimpleNamespace(
            pk=14,
            is_superuser=True,
            has_perm=lambda _permission: True,
        )
        self.product = SimpleNamespace(creado_por_id=self.owner.pk)
        self.unowned_product = SimpleNamespace(creado_por_id=None)

    def test_solo_creador_o_superusuario_puede_editar(self):
        self.assertTrue(_puede_editar_producto(self.owner, self.product))
        self.assertFalse(_puede_editar_producto(self.other_user, self.product))
        self.assertTrue(_puede_editar_producto(self.authorized_staff, self.product))
        self.assertTrue(_puede_editar_producto(self.superuser, self.product))

    def test_productos_anteriores_sin_creador_solo_son_editables_por_superusuario(self):
        self.assertFalse(_puede_editar_producto(self.owner, self.unowned_product))
        self.assertTrue(_puede_editar_producto(self.authorized_staff, self.unowned_product))
        self.assertTrue(_puede_editar_producto(self.superuser, self.unowned_product))

    def test_acceso_de_otro_usuario_se_deniega(self):
        with self.assertRaises(PermissionDenied):
            _verificar_permiso_producto(self.other_user, self.product)


class CalculoStockTests(SimpleTestCase):
    def test_clasifica_stock_bajo_agotado_y_disponible(self):
        self.assertEqual(clasificar_stock(0), "agotado")
        self.assertEqual(clasificar_stock(1), "bajo")
        self.assertEqual(clasificar_stock(5), "bajo")
        self.assertEqual(clasificar_stock(6), "disponible")

    def test_clasificacion_rechaza_stock_negativo(self):
        with self.assertRaises(ValueError):
            clasificar_stock(-1)

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


class HistorialFiltroTests(SimpleTestCase):
    def test_rechaza_rango_de_fechas_invertido(self):
        form = HistorialFiltroForm({
            "desde": "2026-11-02",
            "hasta": "2026-11-01",
        })

        self.assertFalse(form.is_valid())
        self.assertIn(
            "La fecha «Desde» no puede ser posterior a «Hasta».",
            form.non_field_errors(),
        )

    def test_acepta_fechas_en_orden(self):
        form = HistorialFiltroForm({
            "desde": "2026-11-01",
            "hasta": "2026-11-02",
        })

        self.assertTrue(form.is_valid(), form.errors)
