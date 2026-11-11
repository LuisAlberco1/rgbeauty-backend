from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


LEGACY_USER_REFERENCES = {
    "horario_usuario": "fk_horario_usuario_usuario",
    "reserva": "fk_reserva_usuario",
    "venta": "fk_venta_usuario",
}


def _copy_legacy_roles(apps, schema_editor, user_map):
    connection = schema_editor.connection
    database = connection.alias
    tables = set(connection.introspection.table_names())
    if not {"rol", "permiso", "rol_permiso", "usuario_rol"}.issubset(tables):
        return

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    content_type, _ = ContentType.objects.using(database).get_or_create(
        app_label="inventario",
        model="legacypermission",
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT id_rol, nombre, activo FROM rol")
        role_rows = cursor.fetchall()
        cursor.execute(
            "SELECT id_permiso, nombre, modulo, accion, activo FROM permiso"
        )
        permission_rows = cursor.fetchall()
        cursor.execute("SELECT id_rol, id_permiso FROM rol_permiso")
        role_permissions = cursor.fetchall()
        cursor.execute("SELECT id_usuario, id_rol FROM usuario_rol")
        user_roles = cursor.fetchall()

    groups = {}
    for role_id, name, active in role_rows:
        group, _ = Group.objects.using(database).get_or_create(name=name)
        groups[role_id] = (group, bool(active))

    permissions = {}
    for permission_id, name, module, action, active in permission_rows:
        if not active:
            continue
        codename = slugify(f"{module}_{action}").replace("-", "_")[:90]
        if not codename:
            codename = f"legacy_permission_{permission_id}"
        if Permission.objects.using(database).filter(
            content_type_id=content_type.pk,
            codename=codename,
        ).exists():
            codename = f"{codename[:85]}_{permission_id}"
        permission, _ = Permission.objects.using(database).get_or_create(
            content_type_id=content_type.pk,
            codename=codename,
            defaults={"name": name[:255]},
        )
        permissions[permission_id] = permission

    for role_id, permission_id in role_permissions:
        role = groups.get(role_id)
        permission = permissions.get(permission_id)
        if role and role[1] and permission:
            role[0].permissions.add(permission)

    for legacy_user_id, role_id in user_roles:
        mapped_user_id = user_map.get(legacy_user_id)
        role = groups.get(role_id)
        if mapped_user_id and role and role[1]:
            User.objects.using(database).get(pk=mapped_user_id).groups.add(role[0])


def _move_external_user_references(apps, schema_editor, user_map):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    tables = set(connection.introspection.table_names())
    AuthUser = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    user_table = AuthUser._meta.db_table
    quote = schema_editor.quote_name

    with connection.cursor() as cursor:
        plans = []
        for table_name, constraint_name in LEGACY_USER_REFERENCES.items():
            if table_name not in tables:
                continue

            constraints = connection.introspection.get_constraints(cursor, table_name)
            foreign_keys = [
                name
                for name, constraint in constraints.items()
                if constraint.get("foreign_key")
                and constraint["foreign_key"][0] == "usuario"
            ]
            if not foreign_keys:
                continue

            cursor.execute(
                f"SELECT DISTINCT `id_usuario` FROM {quote(table_name)}"
            )
            referenced_ids = {row[0] for row in cursor.fetchall()}
            missing_ids = referenced_ids.difference(user_map)
            if missing_ids:
                raise RuntimeError(
                    f"No se puede migrar {table_name}: hay referencias a usuarios "
                    "de negocio sin una cuenta Django asociada."
                )
            plans.append((table_name, constraint_name, foreign_keys))

        for table_name, constraint_name, foreign_keys in plans:
            for name in foreign_keys:
                cursor.execute(
                    f"ALTER TABLE {quote(table_name)} "
                    f"DROP FOREIGN KEY {quote(name)}"
                )

            for legacy_id, django_id in user_map.items():
                cursor.execute(
                    f"UPDATE {quote(table_name)} SET `id_usuario` = %s "
                    "WHERE `id_usuario` = %s",
                    [-django_id, legacy_id],
                )
            cursor.execute(
                f"UPDATE {quote(table_name)} SET `id_usuario` = -`id_usuario` "
                "WHERE `id_usuario` < 0"
            )
            cursor.execute(
                f"ALTER TABLE {quote(table_name)} "
                f"ADD CONSTRAINT {quote(constraint_name)} "
                f"FOREIGN KEY (`id_usuario`) REFERENCES {quote(user_table)} (`id`)"
            )


def migrate_legacy_accounts(apps, schema_editor):
    connection = schema_editor.connection
    database = connection.alias
    LegacyUser = apps.get_model("inventario", "UsuarioNegocio")
    Persona = apps.get_model("inventario", "Persona")
    Movement = apps.get_model("inventario", "MovimientoInventario")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    user_map = {}
    for legacy_user in LegacyUser.objects.using(database).select_related("persona").iterator():
        user = User.objects.using(database).filter(
            username=legacy_user.nombre_usuario
        ).first()
        if user is None:
            person = legacy_user.persona
            user = User(
                username=legacy_user.nombre_usuario,
                first_name=person.nombre,
                last_name=" ".join(
                    part for part in (
                        person.apellido_paterno,
                        person.apellido_materno,
                    ) if part
                ),
                email=person.email,
                is_active=legacy_user.activo,
                password=make_password(None),
            )
            user.save(using=database)

        person = legacy_user.persona
        if person.django_user_id not in (None, user.pk):
            raise RuntimeError(
                f"El perfil de «{legacy_user.nombre_usuario}» ya está vinculado "
                "a otra cuenta Django."
            )
        if person.django_user_id is None:
            Persona.objects.using(database).filter(pk=person.pk).update(
                django_user_id=user.pk
            )
        user_map[legacy_user.pk] = user.pk

    for movement_id, legacy_user_id, legacy_username in (
        Movement.objects.using(database)
        .values_list("pk", "usuario_id", "usuario__nombre_usuario")
        .iterator()
    ):
        django_user_id = user_map.get(legacy_user_id)
        if django_user_id is None:
            raise RuntimeError(
                f"El movimiento {movement_id} no tiene una cuenta Django "
                "asociada; se canceló la migración para conservar su historial."
            )
        Movement.objects.using(database).filter(pk=movement_id).update(
            actor_django_id=django_user_id,
            usuario_nombre_historico=legacy_username,
        )

    _copy_legacy_roles(apps, schema_editor, user_map)
    _move_external_user_references(apps, schema_editor, user_map)

    if connection.vendor == "mysql":
        tables = set(connection.introspection.table_names())
        with connection.cursor() as cursor:
            for table_name in ("usuario_rol", "rol_permiso", "rol", "permiso"):
                if table_name in tables:
                    cursor.execute(
                        f"DROP TABLE {schema_editor.quote_name(table_name)}"
                    )


def irreversible_reverse(apps, schema_editor):
    raise migrations.IrreversibleError(
        "Los usuarios y roles heredados se migraron a las tablas de autenticación "
        "de Django; restaura una copia de seguridad para revertir este cambio."
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("inventario", "0006_stock_orm_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="persona",
            name="django_user",
            field=models.OneToOneField(
                blank=True,
                db_column="django_user_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="perfil_persona",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="actor_django",
            field=models.ForeignKey(
                db_column="id_usuario_django",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="movimientos_inventario",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="usuario_nombre_historico",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_legacy_accounts, irreversible_reverse),
        migrations.RemoveField(
            model_name="movimientoinventario",
            name="usuario",
        ),
        migrations.RenameField(
            model_name="movimientoinventario",
            old_name="actor_django",
            new_name="usuario",
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="usuario",
            field=models.ForeignKey(
                db_column="id_usuario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="movimientos_inventario",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.DeleteModel(
            name="UsuarioNegocio",
        ),
    ]
