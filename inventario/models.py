from django.conf import settings
from django.db import models
from django.utils import timezone


class CategoriaProducto(models.Model):
    """Modelo de lectura/escritura para la tabla existente categoria_producto."""
    id_categoria_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "categoria_producto"
        ordering = ["nombre"]
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de productos"

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    id_marca = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "marca"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.PROTECT,
        db_column="id_categoria_producto",
        related_name="productos",
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        db_column="id_marca",
        related_name="productos",
    )
    sku = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="creado_por_id",
        related_name="productos_creados",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)
    archivado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "producto"
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.sku} - {self.nombre}"


class ProductoImagen(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="imagenes",
    )
    url = models.CharField(max_length=500)
    texto_alternativo = models.CharField(max_length=255, blank=True, null=True)
    orden = models.PositiveIntegerField(default=1)
    principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "producto_imagen"
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "orden"],
                name="id_producto",
            ),
        ]

    @property
    def image_src(self):
        from django.core.files.storage import default_storage

        return default_storage.url(self.url)

    def __str__(self):
        return self.texto_alternativo or f"Imagen de {self.producto.nombre}"


class ProductoPrecio(models.Model):
    id_precio = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="precios",
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "producto_precio"
        ordering = ["-fecha_inicio"]
        verbose_name = "Precio de producto"
        verbose_name_plural = "Precios de productos"

    def __str__(self):
        return f"{self.producto.nombre} - ${self.precio}"


class Inventario(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    ubicacion = models.CharField(max_length=150, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "inventario"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Stock(models.Model):
    id_stock = models.AutoField(primary_key=True)
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.PROTECT,
        db_column="id_inventario",
        related_name="existencias",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="existencias",
    )
    cantidad_actual = models.PositiveIntegerField(default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock"
        verbose_name = "Existencia"
        verbose_name_plural = "Existencias"
        unique_together = (("inventario", "producto"),)

    def __str__(self):
        return f"{self.producto} - {self.inventario}: {self.cantidad_actual}"


class TipoMovimiento(models.Model):
    id_tipo_movimiento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    afecta_stock = models.BooleanField(default=True)

    class Meta:
        db_table = "tipo_movimiento"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class MovimientoInventario(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.PROTECT,
        db_column="id_inventario",
        related_name="movimientos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="movimientos_inventario",
    )
    usuario_nombre_historico = models.CharField(max_length=150, blank=True)
    tipo_movimiento = models.ForeignKey(
        TipoMovimiento,
        on_delete=models.PROTECT,
        db_column="id_tipo_movimiento",
        related_name="movimientos",
    )
    fecha = models.DateTimeField()
    motivo = models.CharField(max_length=255)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "movimiento_inventario"
        ordering = ["-fecha", "-id_movimiento"]
        permissions = [
            ("register_stock_movement", "Can register stock entries and exits"),
            ("adjust_stock", "Can adjust stock counts"),
        ]


class RegistroAcceso(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="registros_acceso",
        null=True,
        blank=True,
    )
    nombre_usuario = models.CharField(max_length=150)
    clave_sesion_hash = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
    )
    inicio = models.DateTimeField(default=timezone.now)
    cierre = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-inicio", "-pk"]
        permissions = [
            ("manage_team_accounts", "Can manage team accounts and roles"),
            ("view_access_history", "Can view account access history"),
        ]

    def __str__(self):
        return f"{self.nombre_usuario} - {self.inicio:%Y-%m-%d %H:%M}"


class DetalleMovimiento(models.Model):
    id_detalle_movimiento = models.AutoField(primary_key=True)
    movimiento = models.ForeignKey(
        MovimientoInventario,
        on_delete=models.PROTECT,
        db_column="id_movimiento",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="detalles_movimiento",
    )
    cantidad = models.PositiveIntegerField()
    stock_anterior = models.PositiveIntegerField()
    stock_nuevo = models.PositiveIntegerField()

    class Meta:
        db_table = "detalle_movimiento"
        