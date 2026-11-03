from django.conf import settings
from django.db import models
 

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
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "producto"
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.sku} - {self.nombre}"


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
        managed = False
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class TipoMovimiento(models.Model):
    id_tipo_movimiento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    afecta_stock = models.BooleanField(default=True)

    class Meta:
        db_table = "tipo_movimiento"
        managed = False
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=150, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "persona"
        managed = False


class UsuarioNegocio(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    persona = models.OneToOneField(
        Persona,
        on_delete=models.PROTECT,
        db_column="id_persona",
        related_name="usuario_negocio",
    )
    nombre_usuario = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultimo_acceso = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "usuario"
        managed = False

    def __str__(self):
        return self.nombre_usuario


class MovimientoInventario(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.PROTECT,
        db_column="id_inventario",
        related_name="movimientos",
    )
    usuario = models.ForeignKey(
        UsuarioNegocio,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="movimientos",
    )
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
        managed = False
        ordering = ["-fecha", "-id_movimiento"]


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
        managed = False
