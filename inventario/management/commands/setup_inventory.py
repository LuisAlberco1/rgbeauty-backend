import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from inventario.initial_setup import configure_roles, configure_stock
from inventario.roles import ADMIN_GROUP_NAME


class Command(BaseCommand):
    help = (
        "Prepara roles e inventario, y solicita la cuenta inicial de la dueña "
        "si todavía no existe."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            configure_roles()
        except Permission.DoesNotExist as exc:
            raise CommandError(str(exc)) from exc
        configure_stock()
        self.stdout.write("Roles e inventario inicial configurados.")

        User = get_user_model()
        administrator_group = Group.objects.get(name=ADMIN_GROUP_NAME)
        if administrator_group.user_set.filter(is_active=True).exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "Ya existe una cuenta Administradora activa; se conserva."
                )
            )
            return

        owner = self._create_owner(User, administrator_group)
        self.stdout.write(
            self.style.SUCCESS(
                f"Cuenta Administradora «{owner.get_username()}» creada. "
                "Puede iniciar sesión en la aplicación; no necesita Django Admin."
            )
        )

    def _create_owner(self, User, administrator_group):
        username_field = User.USERNAME_FIELD
        username = input(f"Usuario de la dueña ({username_field}): ").strip()
        if not username:
            raise CommandError("El usuario no puede estar vacío.")

        username_model_field = User._meta.get_field(username_field)
        candidate = User(**{username_field: username})
        try:
            username_model_field.clean(username, candidate)
        except ValidationError as exc:
            raise CommandError("El nombre de usuario no es válido: " + "; ".join(exc.messages)) from exc

        if User._default_manager.filter(
            **{f"{username_field}__iexact": username}
        ).exists():
            raise CommandError("Ya existe una cuenta con ese nombre de usuario.")

        email = input("Correo electrónico: ").strip()
        if email:
            try:
                validate_email(email)
            except ValidationError as exc:
                raise CommandError("El correo electrónico no es válido.") from exc

        password = getpass.getpass("Contraseña de la dueña: ")
        password_confirmation = getpass.getpass("Repite la contraseña: ")
        if password != password_confirmation:
            raise CommandError("Las contraseñas no coinciden.")

        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            raise CommandError("La contraseña no es válida: " + "; ".join(exc.messages)) from exc

        owner = User._default_manager.create_user(
            **{
                username_field: username,
                "email": email,
                "password": password,
            }
        )
        administrator_group.user_set.add(owner)
        return owner
