from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Inventario, Producto, RegistroAcceso, Stock
from .session_utils import ACCESS_RECORD_SESSION_KEY, hash_session_key


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


@receiver(user_logged_in, dispatch_uid="inventario.registrar_inicio_sesion")
def registrar_inicio_sesion(sender, request, user, **kwargs):
    session_key = request.session.session_key
    if session_key:
        registro, _ = RegistroAcceso.objects.get_or_create(
            clave_sesion_hash=hash_session_key(session_key),
            defaults={
                "usuario": user,
                "nombre_usuario": user.get_username(),
                "inicio": timezone.now(),
            },
        )
        request.session[ACCESS_RECORD_SESSION_KEY] = registro.pk


@receiver(user_logged_out, dispatch_uid="inventario.registrar_cierre_sesion")
def registrar_cierre_sesion(sender, request, user, **kwargs):
    registro_id = request.session.get(ACCESS_RECORD_SESSION_KEY)
    if registro_id:
        RegistroAcceso.objects.filter(
            pk=registro_id,
            cierre__isnull=True,
        ).update(cierre=timezone.now())
        return

    session_key = request.session.session_key
    if session_key:
        RegistroAcceso.objects.filter(
            clave_sesion_hash=hash_session_key(session_key),
            cierre__isnull=True,
        ).update(cierre=timezone.now())
