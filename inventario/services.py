from dataclasses import dataclass

from django.db import connection, transaction
from django.utils import timezone

from .models import (
    DetalleMovimiento,
    Inventario,
    MovimientoInventario,
    Producto,
    TipoMovimiento,
    UsuarioNegocio,
)

MAX_STOCK = 2_147_483_647


class MovimientoStockError(Exception):
    pass


def _validar_tipo_y_cantidad(tipo: str, cantidad: int) -> None:
    if tipo not in {"Entrada", "Salida", "Ajuste"}:
        raise MovimientoStockError("El tipo de movimiento no es válido.")
    if cantidad < 0:
        raise MovimientoStockError("La cantidad no puede ser negativa.")
    if tipo != "Ajuste" and cantidad == 0:
        raise MovimientoStockError("La cantidad del movimiento debe ser mayor que cero.")


def calcular_stock_nuevo(tipo: str, cantidad: int, stock_anterior: int) -> int:
    _validar_tipo_y_cantidad(tipo, cantidad)
    if stock_anterior < 0:
        raise MovimientoStockError("Las cantidades de stock no pueden ser negativas.")

    if tipo == "Entrada":
        stock_nuevo = stock_anterior + cantidad
    elif tipo == "Salida":
        if cantidad > stock_anterior:
            raise MovimientoStockError(
                f"No hay stock suficiente. Disponible: {stock_anterior} unidades."
            )
        stock_nuevo = stock_anterior - cantidad
    else:
        stock_nuevo = cantidad

    if stock_nuevo > MAX_STOCK:
        raise MovimientoStockError("La cantidad resultante supera el límite admitido por el inventario.")
    return stock_nuevo


@dataclass(frozen=True)
class ResultadoMovimiento:
    movimiento: MovimientoInventario | None
    stock_anterior: int
    stock_nuevo: int


@transaction.atomic
def registrar_movimiento_stock(
    *,
    inventario_id: int,
    producto_id: int,
    tipo: str,
    cantidad: int,
    motivo: str,
    observacion: str,
    nombre_usuario: str,
) -> ResultadoMovimiento:
    _validar_tipo_y_cantidad(tipo, cantidad)

    try:
        inventario = Inventario.objects.select_for_update().get(
            pk=inventario_id, activo=True
        )
    except Inventario.DoesNotExist as exc:
        raise MovimientoStockError("El inventario seleccionado no está activo.") from exc

    try:
        producto = Producto.objects.select_for_update().get(
            pk=producto_id, activo=True
        )
    except Producto.DoesNotExist as exc:
        raise MovimientoStockError("El producto seleccionado no está activo.") from exc

    try:
        usuario = UsuarioNegocio.objects.only(
            "id_usuario", "nombre_usuario", "activo"
        ).select_for_update().get(
            nombre_usuario=nombre_usuario,
            activo=True,
        )
    except UsuarioNegocio.DoesNotExist as exc:
        raise MovimientoStockError(
            "Tu cuenta no está vinculada a un usuario activo del sistema de negocio. "
            "Contacta al administrador para habilitarla."
        ) from exc

    try:
        tipo_movimiento = TipoMovimiento.objects.get(nombre=tipo, afecta_stock=True)
    except TipoMovimiento.DoesNotExist as exc:
        raise MovimientoStockError(
            f"No está configurado el tipo de movimiento «{tipo}». "
            "Ejecuta el comando de inicialización de inventario."
        ) from exc

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO stock (id_inventario, id_producto, cantidad_actual)
            VALUES (%s, %s, 0)
            ON DUPLICATE KEY UPDATE cantidad_actual = cantidad_actual
            """,
            [inventario.pk, producto.pk],
        )
        cursor.execute(
            """
            SELECT cantidad_actual
            FROM stock
            WHERE id_inventario = %s AND id_producto = %s
            FOR UPDATE
            """,
            [inventario.pk, producto.pk],
        )
        fila_stock = cursor.fetchone()

    if fila_stock is None:
        raise MovimientoStockError("No se pudo obtener el stock del producto.")

    stock_anterior = int(fila_stock[0])
    stock_nuevo = calcular_stock_nuevo(tipo, cantidad, stock_anterior)

    if stock_nuevo == stock_anterior:
        return ResultadoMovimiento(None, stock_anterior, stock_nuevo)

    movimiento = MovimientoInventario.objects.create(
        inventario=inventario,
        usuario=usuario,
        tipo_movimiento=tipo_movimiento,
        fecha=timezone.now(),
        motivo=motivo,
        observacion=observacion or None,
    )
    DetalleMovimiento.objects.create(
        movimiento=movimiento,
        producto=producto,
        cantidad=abs(stock_nuevo - stock_anterior),
        stock_anterior=stock_anterior,
        stock_nuevo=stock_nuevo,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE stock
            SET cantidad_actual = %s, fecha_actualizacion = %s
            WHERE id_inventario = %s AND id_producto = %s
            """,
            [stock_nuevo, timezone.now(), inventario.pk, producto.pk],
        )
        if cursor.rowcount != 1:
            raise MovimientoStockError("No se pudo actualizar el stock del producto.")

    return ResultadoMovimiento(movimiento, stock_anterior, stock_nuevo)
