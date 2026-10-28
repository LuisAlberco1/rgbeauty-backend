from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import CategoriaProducto 


CATEGORIAS = [
    ("Cremas", "productos tipo crema"  )
] 


class Command (BaseCommand):
    help = 'Carga las categoria iniciales' 
    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Elimina todas las categorías antes de sembrar",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            CategoriaProducto.objects.all().delete()
            self.stdout.write("Categorías eliminadas.")

        creadas = actualizadas = 0
        for nombre, descripcion in CATEGORIAS:
            # nombre es la clave de búsqueda; la descripción se actualiza si cambia
            _, creada = CategoriaProducto.objects.update_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion},
            )
            if creada:
                creadas += 1
            else:
                actualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {creadas} creadas, {actualizadas} actualizadas."
            )
        )