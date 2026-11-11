import io
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.test import override_settings
from django.contrib.auth.models import Group
from django.db import connection
from django.utils import timezone
from PIL import Image

from .forms import HistorialFiltroForm
from .initial_setup import configure_roles
from .management.commands.setup_inventory import Command as SetupInventoryCommand
from .models import (
    CategoriaProducto,
    Inventario,
    Marca,
    MovimientoInventario,
    Producto,
    ProductoImagen,
    ProductoPrecio,
    RegistroAcceso,
    Stock,
    TipoMovimiento,
    DetalleMovimiento,
)
from .services import (
    MovimientoStockError,
    calcular_stock_nuevo,
    clasificar_stock,
    registrar_movimiento_stock,
)
from .session_utils import hash_session_key
from .roles import (
    ADMIN_GROUP_NAME,
    ASSISTANT_GROUP_NAME,
    LEGACY_INVENTORY_GROUP_NAME,
)
from .views import (
    _puede_editar_producto,
    _verificar_permiso_producto,
)


class SetupInitialRolesTests(TestCase):
    def test_creates_roles_and_limits_assistant_permissions_idempotently(self):
        legacy_user = get_user_model().objects.create_user(
            username="legacy-assistant",
            password="StrongPass#1234",
        )
        Group.objects.get_or_create(name=LEGACY_INVENTORY_GROUP_NAME)
        legacy_user.groups.add(Group.objects.get(name=LEGACY_INVENTORY_GROUP_NAME))

        configure_roles()
        configure_roles()

        group = Group.objects.get(name=LEGACY_INVENTORY_GROUP_NAME)
        self.assertEqual(
            Group.objects.filter(name=LEGACY_INVENTORY_GROUP_NAME).count(),
            1,
        )
        self.assertFalse(group.permissions.filter(codename="change_producto").exists())
        assistant = Group.objects.get(name=ASSISTANT_GROUP_NAME)
        self.assertTrue(
            assistant.permissions.filter(codename="register_stock_movement").exists()
        )
        self.assertFalse(
            assistant.permissions.filter(codename="adjust_stock").exists()
        )
        administrator = Group.objects.get(name=ADMIN_GROUP_NAME)
        self.assertTrue(
            administrator.permissions.filter(codename="manage_team_accounts").exists()
        )
        legacy_user.refresh_from_db()
        self.assertTrue(legacy_user.groups.filter(name=ASSISTANT_GROUP_NAME).exists())
        self.assertFalse(
            legacy_user.groups.filter(name=LEGACY_INVENTORY_GROUP_NAME).exists()
        )


class SetupInventoryCommandTests(TestCase):
    def test_command_configures_application_and_creates_owner_account(self):
        with (
            patch("builtins.input", side_effect=["owner", "owner@example.com"]),
            patch(
                "getpass.getpass",
                side_effect=["StrongPass#1234", "StrongPass#1234"],
            ),
        ):
            SetupInventoryCommand().handle()

        owner = get_user_model().objects.get(username="owner")
        self.assertTrue(owner.is_active)
        self.assertFalse(owner.is_staff)
        self.assertFalse(owner.is_superuser)
        self.assertTrue(owner.groups.filter(name=ADMIN_GROUP_NAME).exists())
        self.assertTrue(Group.objects.filter(name=ASSISTANT_GROUP_NAME).exists())
        self.assertTrue(Inventario.objects.filter(activo=True).exists())
        self.assertTrue(
            TipoMovimiento.objects.filter(nombre__in=["Entrada", "Salida"]).count()
            == 2
        )

    def test_command_does_not_prompt_if_an_active_application_owner_exists(self):
        configure_roles()
        owner = get_user_model().objects.create_user(
            username="existing-owner",
            password="StrongPass#1234",
        )
        owner.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))

        with patch("builtins.input") as input_mock:
            SetupInventoryCommand().handle()

        input_mock.assert_not_called()
        self.assertEqual(get_user_model().objects.filter(is_superuser=True).count(), 0)


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

    def test_persona_table_remains_for_customer_and_address_records(self):
        self.assertIn("persona", connection.introspection.table_names())


class GestionCuentasEquipoTests(TestCase):
    def setUp(self):
        configure_roles()
        user_model = get_user_model()
        self.owner = user_model.objects.create_superuser(
            username="team-owner",
            email="owner@example.com",
            password="StrongPass#1234",
        )
        self.assistant = user_model.objects.create_user(
            username="team-assistant",
            email="assistant@example.com",
            password="StrongPass#1234",
        )

    def test_only_superusers_can_manage_team_accounts(self):
        self.client.force_login(self.assistant)

        response = self.client.get("/equipo/")

        self.assertEqual(response.status_code, 403)

    def test_owner_can_create_assistant_account_with_django_group(self):
        self.client.force_login(self.owner)

        response = self.client.post("/equipo/nueva/", {
            "username": "new-assistant",
            "first_name": "Ana",
            "last_name": "Asistente",
            "email": "ana@example.com",
            "role": ASSISTANT_GROUP_NAME,
            "is_active": "on",
            "password1": "StrongPass#5678",
            "password2": "StrongPass#5678",
        })

        self.assertRedirects(response, "/equipo/")
        new_user = get_user_model().objects.get(username="new-assistant")
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.groups.filter(name=ASSISTANT_GROUP_NAME).exists())
        self.assertTrue(new_user.check_password("StrongPass#5678"))
        self.assertEqual(new_user.first_name, "Ana")
        self.assertEqual(new_user.last_name, "Asistente")
        self.assertEqual(new_user.email, "ana@example.com")

    def test_owner_can_create_a_non_superuser_administrator_account(self):
        self.client.force_login(self.owner)

        response = self.client.post("/equipo/nueva/", {
            "username": "store-manager",
            "first_name": "Nueva",
            "last_name": "Administradora",
            "email": "manager@example.com",
            "role": ADMIN_GROUP_NAME,
            "is_active": "on",
            "password1": "StrongPass#5678",
            "password2": "StrongPass#5678",
        })

        self.assertRedirects(response, "/equipo/")
        manager = get_user_model().objects.get(username="store-manager")
        self.assertFalse(manager.is_superuser)
        self.assertTrue(manager.groups.filter(name=ADMIN_GROUP_NAME).exists())
        self.client.force_login(manager)
        self.assertEqual(self.client.get("/equipo/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_owner_must_provide_account_name_and_email(self):
        self.client.force_login(self.owner)

        response = self.client.post("/equipo/nueva/", {
            "username": "incomplete-assistant",
            "role": ASSISTANT_GROUP_NAME,
            "is_active": "on",
            "password1": "StrongPass#5678",
            "password2": "StrongPass#5678",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="incomplete-assistant").exists()
        )

    def test_owner_cannot_assign_an_email_already_used_by_another_account(self):
        self.client.force_login(self.owner)

        response = self.client.post("/equipo/nueva/", {
            "username": "duplicate-email-assistant",
            "first_name": "Nueva",
            "last_name": "Asistente",
            "email": self.assistant.email,
            "role": ASSISTANT_GROUP_NAME,
            "is_active": "on",
            "password1": "StrongPass#5678",
            "password2": "StrongPass#5678",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe una cuenta con ese correo electrónico.")
        self.assertFalse(
            get_user_model().objects.filter(username="duplicate-email-assistant").exists()
        )

    def test_owner_can_deactivate_account_without_deleting_it(self):
        self.client.force_login(self.owner)

        response = self.client.post(f"/equipo/{self.assistant.pk}/estado/")

        self.assertRedirects(response, "/equipo/")
        self.assistant.refresh_from_db()
        self.assertFalse(self.assistant.is_active)
        self.assertTrue(
            get_user_model().objects.filter(pk=self.assistant.pk).exists()
        )

    def test_last_administrator_cannot_deactivate_their_own_account(self):
        manager = get_user_model().objects.create_user(
            username="only-manager",
            email="only-manager@example.com",
            password="StrongPass#1234",
        )
        manager.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.client.force_login(manager)

        response = self.client.post(f"/equipo/{manager.pk}/estado/", follow=True)

        self.assertEqual(response.status_code, 200)
        manager.refresh_from_db()
        self.assertTrue(manager.is_active)
        self.assertContains(response, "No puedes desactivar tu propia cuenta.")

    def test_last_administrator_cannot_change_their_role_to_assistant(self):
        manager = get_user_model().objects.create_user(
            username="only-manager-role",
            first_name="Única",
            last_name="Administradora",
            email="only-manager-role@example.com",
            password="StrongPass#1234",
        )
        manager.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.client.force_login(manager)

        response = self.client.post(f"/equipo/{manager.pk}/editar/", {
            "username": manager.username,
            "first_name": manager.first_name,
            "last_name": manager.last_name,
            "email": manager.email,
            "role": ASSISTANT_GROUP_NAME,
            "is_active": "on",
        })

        self.assertEqual(response.status_code, 200)
        manager.refresh_from_db()
        self.assertTrue(manager.groups.filter(name=ADMIN_GROUP_NAME).exists())
        self.assertContains(response, "Crea otra cuenta Administradora primero.")

    def test_only_owner_can_view_access_history(self):
        self.client.force_login(self.assistant)

        response = self.client.get("/cuenta/accesos/")

        self.assertEqual(response.status_code, 403)

    def test_owner_sees_current_sessions_and_login_history(self):
        self.client.force_login(self.owner)

        account_response = self.client.get("/cuenta/")
        response = self.client.get("/cuenta/accesos/")

        self.assertContains(account_response, "Gestionar cuentas")
        self.assertContains(account_response, "Ver historial de accesos")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "team-owner")
        self.assertContains(response, "Activa")
        self.assertEqual(RegistroAcceso.objects.filter(usuario=self.owner).count(), 1)

    def test_assistant_account_page_does_not_show_management_actions(self):
        self.client.force_login(self.assistant)

        response = self.client.get("/cuenta/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Administración del equipo")

    def test_superuser_can_switch_to_application_administrator(self):
        self.client.force_login(self.owner)

        response = self.client.post("/cuenta/activar-administradora/")

        self.assertRedirects(response, "/cuenta/")
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_superuser)
        self.assertFalse(self.owner.is_staff)
        self.assertTrue(self.owner.has_perm("inventario.manage_team_accounts"))
        self.assertEqual(self.client.get("/equipo/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)


class PermisosAsistentaTests(TestCase):
    def setUp(self):
        configure_roles()
        self.user = get_user_model().objects.create_user(
            username="assistant-role",
            email="assistant-role@example.com",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
        self.client.force_login(self.user)

    def test_assistant_can_view_catalog_stock_and_register_movements(self):
        catalog = self.client.get("/productos/")
        self.assertEqual(catalog.status_code, 200)
        self.assertNotContains(catalog, "Nuevo producto")
        self.assertNotContains(catalog, "Mis productos")
        self.assertEqual(self.client.get("/stock/").status_code, 200)
        self.assertEqual(self.client.get("/movimientos/nuevo/").status_code, 200)

    def test_assistant_cannot_adjust_stock_manage_products_or_view_audit_history(self):
        self.assertEqual(self.client.get("/ajustes-stock/").status_code, 403)
        self.assertEqual(self.client.get("/historial/").status_code, 403)
        self.assertEqual(self.client.get("/productos/nuevo/").status_code, 403)
        self.assertEqual(self.client.get("/categorias/").status_code, 403)
        self.assertEqual(self.client.get("/marcas/").status_code, 403)
        self.assertEqual(self.client.get("/equipo/").status_code, 403)

    def test_assistant_can_record_a_stock_entry(self):
        inventory = Inventario.objects.create(nombre="Bodega entrada")
        category = CategoriaProducto.objects.create(nombre="Entrada")
        brand = Marca.objects.create(nombre="Marca entrada")
        product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="ENTRY-001",
            nombre="Producto entrada",
        )
        entry_type = TipoMovimiento.objects.create(nombre="Entrada")
        TipoMovimiento.objects.create(nombre="Salida")

        response = self.client.post("/movimientos/nuevo/", {
            "inventario": str(inventory.pk),
            "producto": str(product.pk),
            "tipo_movimiento": str(entry_type.pk),
            "cantidad": "6",
            "motivo": "Reposición",
            "observacion": "",
        })

        self.assertRedirects(response, "/movimientos/nuevo/")
        self.assertEqual(
            Stock.objects.get(inventario=inventory, producto=product).cantidad_actual,
            6,
        )
        self.assertTrue(
            MovimientoInventario.objects.filter(usuario=self.user).exists()
        )

    def test_catalog_links_to_product_details_and_stock_is_linked_back(self):
        inventory = Inventario.objects.create(nombre="Bodega asistenta")
        category = CategoriaProducto.objects.create(nombre="Cuidado asistenta")
        brand = Marca.objects.create(nombre="Marca asistenta")
        product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="ASSISTANT-001",
            nombre="Producto asistenta",
        )
        Stock.objects.filter(inventario=inventory, producto=product).update(
            cantidad_actual=4
        )

        catalog = self.client.get("/productos/")
        detail = self.client.get(f"/productos/{product.pk}/")
        stock = self.client.get("/stock/")

        self.assertContains(catalog, "Ver detalle y existencias")
        self.assertContains(detail, "Existencias por inventario")
        self.assertContains(detail, ">4</strong>")
        self.assertContains(detail, "unidades.")
        self.assertContains(detail, "Registrar entrada o salida")
        self.assertContains(stock, f'href="/productos/{product.pk}/"')

    def test_product_detail_prefills_movement_form(self):
        inventory = Inventario.objects.create(nombre="Bodega preselección")
        category = CategoriaProducto.objects.create(nombre="Categoría preselección")
        brand = Marca.objects.create(nombre="Marca preselección")
        product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="PREFILL-001",
            nombre="Producto preselección",
        )

        response = self.client.get(f"/movimientos/nuevo/?producto={product.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"]["producto"].value(),
            str(product.pk),
        )


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
        configure_roles()
        self.user_model.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="StrongPass#1234",
        )

        self.user_model.objects.get(username="login-user").groups.add(
            Group.objects.get(name=ASSISTANT_GROUP_NAME)
        )
        response = self.client.post("/login/", {
            "username": "login-user",
            "password": "StrongPass#1234",
        })
        self.assertRedirects(response, "/")
        access_record = RegistroAcceso.objects.get(nombre_usuario="login-user")
        self.assertIsNone(access_record.cierre)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertEqual(self.client.post("/logout/").status_code, 302)
        access_record.refresh_from_db()
        self.assertIsNotNone(access_record.cierre)

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
        self.assertContains(response, "Tipo de cuenta")
        self.assertContains(response, "Asistenta")
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
        access_record = RegistroAcceso.objects.get(usuario=self.user)
        self.assertEqual(
            access_record.clave_sesion_hash,
            hash_session_key(self.client.session.session_key),
        )


class EliminacionCategoriaMarcaTests(TestCase):
    def setUp(self):
        configure_roles()
        self.user = get_user_model().objects.create_user(
            username="catalog-admin",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.category = CategoriaProducto.objects.create(nombre="Categoría eliminable")
        self.brand = Marca.objects.create(nombre="Marca eliminable")
        self.client.force_login(self.user)

    def test_admin_can_delete_unused_category_and_brand(self):
        category_response = self.client.post(
            f"/categorias/{self.category.pk}/eliminar/"
        )
        brand_response = self.client.post(f"/marcas/{self.brand.pk}/eliminar/")

        self.assertRedirects(category_response, "/categorias/")
        self.assertRedirects(brand_response, "/marcas/")
        self.assertFalse(CategoriaProducto.objects.filter(pk=self.category.pk).exists())
        self.assertFalse(Marca.objects.filter(pk=self.brand.pk).exists())

    def test_category_and_brand_with_products_cannot_be_deleted(self):
        Producto.objects.create(
            categoria=self.category,
            marca=self.brand,
            sku="PROTECTED-001",
            nombre="Producto protegido",
        )

        category_response = self.client.post(
            f"/categorias/{self.category.pk}/eliminar/",
            follow=True,
        )
        brand_response = self.client.post(
            f"/marcas/{self.brand.pk}/eliminar/",
            follow=True,
        )

        self.assertContains(category_response, "tiene productos asociados")
        self.assertContains(brand_response, "tiene productos asociados")
        self.assertTrue(CategoriaProducto.objects.filter(pk=self.category.pk).exists())
        self.assertTrue(Marca.objects.filter(pk=self.brand.pk).exists())

    def test_delete_actions_require_post_and_delete_permission(self):
        self.assertEqual(
            self.client.get(f"/categorias/{self.category.pk}/eliminar/").status_code,
            405,
        )
        self.assertEqual(
            self.client.get(f"/marcas/{self.brand.pk}/eliminar/").status_code,
            405,
        )
        self.assertContains(
            self.client.get("/categorias/"),
            "Solo se podrá eliminar si no tiene productos asociados",
        )
        self.assertContains(
            self.client.get("/marcas/"),
            "Solo se podrá eliminar si no tiene productos asociados",
        )


class ProductosPaginacionTests(TestCase):
    def setUp(self):
        configure_roles()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="catalog-user",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
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


class FiltrosEnTiempoRealTests(TestCase):
    def setUp(self):
        configure_roles()
        self.user = get_user_model().objects.create_user(
            username="live-filter-admin",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.client.force_login(self.user)

    def test_all_list_filters_submit_automatically_and_keep_fallback_buttons(self):
        pages = (
            ("/productos/", "products"),
            ("/categorias/", "categories"),
            ("/marcas/", "brands"),
            ("/stock/", "stock-results"),
            ("/historial/", "history-results"),
        )
        for path, results_key in pages:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "data-live-filter")
                self.assertContains(response, "js/live_filters.js")
                self.assertContains(response, "type=\"submit\"")
                self.assertContains(response, f'data-live-results="{results_key}"')


class ProductoDetalleTests(TestCase):
    def setUp(self):
        configure_roles()
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="product-owner",
            password="OwnerPass#1234",
        )
        self.other_user = self.user_model.objects.create_user(
            username="product-viewer",
            password="ViewerPass#1234",
        )
        self.owner.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.other_user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
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


class ImagenProductoTests(TestCase):
    def setUp(self):
        configure_roles()
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.owner = get_user_model().objects.create_user(
            username="image-product-owner",
            password="StrongPass#1234",
        )
        self.owner.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        self.category = CategoriaProducto.objects.create(nombre="Cuidado con imagen")
        self.brand = Marca.objects.create(nombre="Marca con imagen")
        self.client.force_login(self.owner)

    @staticmethod
    def image_upload(name="producto.png", color="red"):
        image_bytes = io.BytesIO()
        Image.new("RGB", (80, 80), color=color).save(image_bytes, format="PNG")
        return SimpleUploadedFile(
            name,
            image_bytes.getvalue(),
            content_type="image/png",
        )

    def product_form_data(self):
        return {
            "sku": "IMAGE-001",
            "nombre": "Producto con imagen",
            "descripcion": "Descripción de producto.",
            "categoria": str(self.category.pk),
            "marca": str(self.brand.pk),
            "precio": "1200.00",
        }

    def test_create_product_uploads_image_and_detail_displays_it(self):
        response = self.client.post(
            "/productos/nuevo/",
            data={
                **self.product_form_data(),
                "imagen": self.image_upload(),
            },
        )

        self.assertRedirects(response, "/productos/")
        product = Producto.objects.get(sku="IMAGE-001")
        product_image = ProductoImagen.objects.get(producto=product)
        self.assertTrue(default_storage.exists(product_image.url))
        self.assertTrue(product_image.principal)

        detail = self.client.get(f"/productos/{product.pk}/")

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, default_storage.url(product_image.url))
        self.assertContains(detail, 'aria-label="Imagen del producto"')

    def test_edit_can_replace_and_remove_product_image(self):
        product = Producto.objects.create(
            categoria=self.category,
            marca=self.brand,
            sku="IMAGE-002",
            nombre="Producto editable con imagen",
        )
        first_file = default_storage.save(
            "productos/old-image.png",
            self.image_upload("old-image.png"),
        )
        product_image = ProductoImagen.objects.create(
            producto=product,
            url=first_file,
            texto_alternativo=product.nombre,
            orden=1,
            principal=True,
        )

        replace_response = self.client.post(
            f"/productos/{product.pk}/editar/",
            data={
                **self.product_form_data(),
                "sku": "IMAGE-002",
                "nombre": product.nombre,
                "imagen": self.image_upload("new-image.png", color="blue"),
            },
        )

        self.assertRedirects(replace_response, "/productos/")
        product_image.refresh_from_db()
        self.assertNotEqual(product_image.url, first_file)
        self.assertFalse(default_storage.exists(first_file))
        self.assertTrue(default_storage.exists(product_image.url))

        remove_response = self.client.post(
            f"/productos/{product.pk}/editar/",
            data={
                **self.product_form_data(),
                "sku": "IMAGE-002",
                "nombre": product.nombre,
                "eliminar_imagen": "on",
            },
        )

        self.assertRedirects(remove_response, "/productos/")
        self.assertFalse(ProductoImagen.objects.filter(pk=product_image.pk).exists())
        self.assertFalse(default_storage.exists(product_image.url))

    def test_invalid_non_image_upload_is_rejected(self):
        response = self.client.post(
            "/productos/nuevo/",
            data={
                **self.product_form_data(),
                "imagen": SimpleUploadedFile(
                    "not-an-image.png",
                    b"not an image",
                    content_type="image/png",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("imagen"))
        self.assertFalse(Producto.objects.filter(sku="IMAGE-001").exists())


class EliminacionPermanenteProductoTests(TestCase):
    def setUp(self):
        configure_roles()
        self.user = get_user_model().objects.create_user(
            username="product-admin-delete",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ADMIN_GROUP_NAME))
        category = CategoriaProducto.objects.create(nombre="Categoría borrar producto")
        brand = Marca.objects.create(nombre="Marca borrar producto")
        self.product = Producto.objects.create(
            categoria=category,
            marca=brand,
            sku="DELETE-001",
            nombre="Producto para borrar",
        )
        self.inventory = Inventario.objects.create(nombre="Bodega borrar producto")
        self.client.force_login(self.user)

    def test_inactive_product_is_removed_from_catalog_and_stock_is_preserved(self):
        stock = Stock.objects.get(inventario=self.inventory, producto=self.product)
        self.product.activo = False
        self.product.save(update_fields=["activo"])

        response = self.client.post(f"/productos/{self.product.pk}/eliminar/")

        self.assertRedirects(response, "/productos/")
        self.product.refresh_from_db()
        self.assertFalse(self.product.activo)
        self.assertTrue(self.product.archivado)
        self.assertTrue(Stock.objects.filter(pk=stock.pk).exists())
        self.assertContains(
            self.client.get("/productos/"),
            "No hay productos para mostrar",
        )
        archived_catalog = self.client.get("/productos/?estado=archivado")
        self.assertContains(archived_catalog, self.product.nombre)
        self.assertContains(archived_catalog, "historial conservado")
        self.assertEqual(self.client.get(f"/productos/{self.product.pk}/").status_code, 200)

    def test_active_product_must_be_deactivated_before_catalog_removal(self):
        response = self.client.post(
            f"/productos/{self.product.pk}/eliminar/",
            follow=True,
        )

        self.assertContains(response, "Desactiva el producto antes de eliminarlo")
        self.assertTrue(Producto.objects.filter(pk=self.product.pk).exists())

    def test_product_price_history_is_preserved_when_removed_from_catalog(self):
        self.product.activo = False
        self.product.save(update_fields=["activo"])
        price = ProductoPrecio.objects.create(producto=self.product, precio="10.00")

        response = self.client.post(
            f"/productos/{self.product.pk}/eliminar/",
            follow=True,
        )

        self.assertContains(response, "Se conservaron sus existencias y todo su historial")
        self.assertTrue(Producto.objects.filter(pk=self.product.pk, archivado=True).exists())
        self.assertTrue(ProductoPrecio.objects.filter(pk=price.pk, producto=self.product).exists())

    def test_stock_is_preserved_when_product_is_removed_from_catalog(self):
        self.product.activo = False
        self.product.save(update_fields=["activo"])
        Stock.objects.filter(
            inventario=self.inventory,
            producto=self.product,
        ).update(cantidad_actual=2)

        response = self.client.post(
            f"/productos/{self.product.pk}/eliminar/",
            follow=True,
        )

        self.assertContains(response, "Se conservaron sus existencias")
        self.assertTrue(Producto.objects.filter(pk=self.product.pk, archivado=True).exists())
        self.assertEqual(
            Stock.objects.get(inventario=self.inventory, producto=self.product).cantidad_actual,
            2,
        )

    def test_movement_history_is_preserved_when_product_is_removed_from_catalog(self):
        movement_type = TipoMovimiento.objects.create(nombre="Entrada archivo")
        movement = MovimientoInventario.objects.create(
            inventario=self.inventory,
            usuario=self.user,
            usuario_nombre_historico=self.user.get_username(),
            tipo_movimiento=movement_type,
            fecha=timezone.now(),
            motivo="Prueba de conservación",
        )
        movement_detail = DetalleMovimiento.objects.create(
            movimiento=movement,
            producto=self.product,
            cantidad=1,
            stock_anterior=0,
            stock_nuevo=1,
        )
        self.product.activo = False
        self.product.save(update_fields=["activo"])

        self.client.post(f"/productos/{self.product.pk}/eliminar/")

        self.assertTrue(
            DetalleMovimiento.objects.filter(
                pk=movement_detail.pk,
                producto=self.product,
                movimiento=movement,
            ).exists()
        )

    def test_archived_product_cannot_be_reactivated_or_edited(self):
        self.product.activo = False
        self.product.archivado = True
        self.product.save(update_fields=["activo", "archivado"])

        self.assertEqual(
            self.client.post(f"/productos/{self.product.pk}/estado/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/productos/{self.product.pk}/editar/").status_code,
            403,
        )

    def test_assistant_cannot_permanently_delete_products(self):
        assistant = get_user_model().objects.create_user(
            username="assistant-delete-denied",
            password="StrongPass#1234",
        )
        assistant.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
        self.client.force_login(assistant)

        response = self.client.post(f"/productos/{self.product.pk}/eliminar/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Producto.objects.filter(pk=self.product.pk).exists())


class StockActualEndpointTests(TestCase):
    def setUp(self):
        configure_roles()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="stock-viewer",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
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
        configure_roles()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="dashboard-viewer",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
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
        configure_roles()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="stock-filter",
            password="StrongPass#1234",
        )
        self.user.groups.add(Group.objects.get(name=ASSISTANT_GROUP_NAME))
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
        self.user = get_user_model().objects.create_user(
            username="movement-user",
            password="StrongPass#1234",
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
            usuario=self.user,
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
        self.assertEqual(
            result.movimiento.usuario_nombre_historico,
            self.user.get_username(),
        )


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

    def test_solo_el_permiso_o_superusuario_permite_editar(self):
        self.assertFalse(_puede_editar_producto(self.owner))
        self.assertFalse(_puede_editar_producto(self.other_user))
        self.assertTrue(_puede_editar_producto(self.authorized_staff))
        self.assertTrue(_puede_editar_producto(self.superuser))

    def test_productos_anteriores_sin_creador_respetan_el_permiso(self):
        self.assertFalse(_puede_editar_producto(self.owner))
        self.assertTrue(_puede_editar_producto(self.authorized_staff))
        self.assertTrue(_puede_editar_producto(self.superuser))

    def test_acceso_de_otro_usuario_se_deniega(self):
        with self.assertRaises(PermissionDenied):
            _verificar_permiso_producto(self.other_user)


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
