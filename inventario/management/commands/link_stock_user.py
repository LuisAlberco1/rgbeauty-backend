from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from inventario.models import Persona, UsuarioNegocio


class Command(BaseCommand):
    help = "Vincula una cuenta Django con el usuario de negocio que registra movimientos."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Nombre de usuario de la cuenta Django.")
        parser.add_argument(
            "--rut",
            help="RUT de la persona responsable. Si se omite, se solicitará de forma interactiva.",
        )

    def _read_value(self, label, default="", required=True):
        prompt = f"{label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = input(prompt).strip() or default
        if required and not value:
            raise CommandError(f"El campo {label} es obligatorio.")
        return value

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip()
        User = get_user_model()
        try:
            django_user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No existe la cuenta Django «{username}».") from exc

        usuario_existente = UsuarioNegocio.objects.filter(
            nombre_usuario=django_user.get_username()
        ).first()
        if usuario_existente:
            if usuario_existente.activo:
                self.stdout.write(
                    self.style.SUCCESS("Esta cuenta ya está vinculada a un usuario de negocio activo.")
                )
                return
            raise CommandError(
                "Ya existe un usuario de negocio inactivo con ese nombre. "
                "Actívalo desde la administración antes de registrar movimientos."
            )

        rut = (options["rut"] or self._read_value("RUT")).strip()
        nombre = self._read_value("Nombre", django_user.first_name)
        apellidos = django_user.last_name.strip().split(maxsplit=1)
        apellido_paterno = self._read_value(
            "Apellido paterno",
            apellidos[0] if apellidos else "",
        )
        apellido_materno = self._read_value(
            "Apellido materno (opcional)",
            apellidos[1] if len(apellidos) > 1 else "",
            required=False,
        )
        email = self._read_value("Correo", django_user.email).strip()

        if not rut:
            raise CommandError("El RUT es obligatorio.")
        if len(username) > 50:
            raise CommandError("El nombre de usuario no puede superar 50 caracteres.")
        if len(rut) > 12:
            raise CommandError("El RUT no puede superar 12 caracteres.")
        if len(nombre) > 100 or len(apellido_paterno) > 100 or len(apellido_materno) > 100:
            raise CommandError("Los nombres y apellidos no pueden superar 100 caracteres.")
        if len(email) > 150:
            raise CommandError("El correo no puede superar 150 caracteres.")
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("Ingresa un correo válido.") from exc

        try:
            persona = Persona.objects.create(
                rut=rut,
                nombre=nombre,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno or None,
                email=email,
            )
            UsuarioNegocio.objects.create(
                persona=persona,
                nombre_usuario=django_user.get_username(),
                password_hash=make_password(None),
                activo=True,
            )
        except IntegrityError as exc:
            raise CommandError(
                "No se pudo vincular la cuenta. Comprueba que el RUT y el correo "
                "no estén registrados en otra persona."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"La cuenta Django «{django_user.get_username()}» quedó vinculada "
                "al usuario de negocio."
            )
        )
