from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Inventario, Producto, Stock


@receiver(post_save, sender=Producto)
def crear_stock_para_producto_activo(sender, instance, **kwargs):
    if not instance.activo:
        return

    Stock.objects.bulk_create(
        [
            Stock(inventario=inventario, producto=instance)
            for inventario in Inventario.objects.filter(activo=True).only("pk")
        ],
        ignore_conflicts=True,
    )


@receiver(post_save, sender=Inventario)
def crear_stock_para_inventario_activo(sender, instance, **kwargs):
    if not instance.activo:
        return

    Stock.objects.bulk_create(
        [
            Stock(inventario=instance, producto=producto)
            for producto in Producto.objects.filter(activo=True).only("pk")
        ],
        ignore_conflicts=True,
    )
