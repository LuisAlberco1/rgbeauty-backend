from django.contrib.auth.models import Group, Permission
from django.db import transaction

from .models import Inventario, TipoMovimiento
from .roles import (
    ADMIN_GROUP_NAME,
    ASSISTANT_GROUP_NAME,
    LEGACY_INVENTORY_GROUP_NAME,
)


@transaction.atomic
def configure_roles():
    permissions = Permission.objects.filter(content_type__app_label="inventario")
    permission_by_codename = {
        permission.codename: permission for permission in permissions
    }
    required_codenames = (
        "view_stock",
        "view_producto",
        "register_stock_movement",
    )
    missing = [name for name in required_codenames if name not in permission_by_codename]
    if missing:
        raise Permission.DoesNotExist(
            "Faltan permisos de inventario. Ejecuta las migraciones antes de configurar la aplicación."
        )

    legacy_group, _ = Group.objects.get_or_create(
        name=LEGACY_INVENTORY_GROUP_NAME
    )
    owner_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    owner_group.permissions.set(permissions)

    assistant_group, _ = Group.objects.get_or_create(name=ASSISTANT_GROUP_NAME)
    assistant_group.permissions.set(
        [
            permission_by_codename["view_producto"],
            permission_by_codename["view_stock"],
            permission_by_codename["register_stock_movement"],
        ]
    )
    legacy_users = list(legacy_group.user_set.all())
    assistant_group.user_set.add(*legacy_users)
    legacy_group.user_set.clear()
    legacy_group.permissions.set(assistant_group.permissions.all())


@transaction.atomic
def configure_stock():
    inventario = Inventario.objects.filter(activo=True).first()
    if inventario is None:
        inventario, _ = Inventario.objects.get_or_create(
            nombre="Bodega principal",
            defaults={
                "descripcion": "Inventario principal de productos.",
                "activo": True,
            },
        )
        if not inventario.activo:
            inventario.activo = True
            inventario.save(update_fields=["activo"])

    for nombre, descripcion in {
        "Entrada": "Ingreso de unidades al inventario.",
        "Salida": "Retiro de unidades del inventario.",
        "Ajuste": "Corrección basada en un conteo físico.",
    }.items():
        TipoMovimiento.objects.update_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "afecta_stock": True},
        )
