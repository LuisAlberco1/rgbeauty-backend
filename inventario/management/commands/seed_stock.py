from django.core.management.base import BaseCommand
from django.db import transaction

from inventario.models import Inventario, TipoMovimiento


TIPOS_MOVIMIENTO = {
    "Entrada": "Ingreso de unidades al inventario.",
    "Salida": "Retiro de unidades del inventario.",
    "Ajuste": "Corrección basada en un conteo físico.",
}


class Command(BaseCommand):
    help = "Prepara los tipos de movimiento y un inventario activo si aún no existen."

    @transaction.atomic
    def handle(self, *args, **options):
        inventario = Inventario.objects.filter(activo=True).first()
        if inventario is None:
            inventario, creado = Inventario.objects.get_or_create(
                nombre="Bodega principal",
                defaults={
                    "descripcion": "Inventario principal de productos.",
                    "activo": True,
                },
            )
            if not inventario.activo:
                inventario.activo = True
                inventario.save(update_fields=["activo"])
            estado = "creado" if creado else "reactivado"
            self.stdout.write(f"Inventario «{inventario.nombre}» {estado}.")
        else:
            self.stdout.write(f"Se usará el inventario activo «{inventario.nombre}».")

        for nombre, descripcion in TIPOS_MOVIMIENTO.items():
            tipo, creado = TipoMovimiento.objects.update_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "afecta_stock": True},
            )
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"Tipo «{tipo.nombre}» {estado}.")

        self.stdout.write(
            self.style.SUCCESS(
                "Configuración lista. El nombre de la cuenta Django debe coincidir "
                "con nombre_usuario en la tabla usuario."
            )
        )
