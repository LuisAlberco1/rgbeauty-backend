from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


GROUP_NAME = "Personal de inventario"
PERMISSION_CODENAME = "change_producto"
PERMISSION_APP_LABEL = "inventario"


class Command(BaseCommand):
    help = (
        "Crea el grupo de personal de inventario y le asigna permiso para editar "
        "productos del catálogo compartido."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        group, group_created = Group.objects.get_or_create(name=GROUP_NAME)
        try:
            permission = Permission.objects.get(
                content_type__app_label=PERMISSION_APP_LABEL,
                codename=PERMISSION_CODENAME,
            )
        except Permission.DoesNotExist as exc:
            self.stderr.write(
                self.style.ERROR(
                    "No existe el permiso de edición de productos. "
                    "Ejecuta primero las migraciones de Django."
                )
            )
            raise exc

        already_assigned = group.permissions.filter(pk=permission.pk).exists()
        group.permissions.add(permission)

        if group_created:
            self.stdout.write(f"Grupo «{GROUP_NAME}» creado.")
        else:
            self.stdout.write(f"Grupo «{GROUP_NAME}» ya existía.")

        if already_assigned:
            self.stdout.write("El permiso de edición ya estaba asignado.")
        else:
            self.stdout.write("Permiso de edición de productos asignado al grupo.")

        self.stdout.write(
            self.style.SUCCESS(
                "Listo. Agrega las cuentas de la dueña y la asistenta a este grupo "
                "desde Django Admin > Autenticación y autorización > Usuarios."
            )
        )
