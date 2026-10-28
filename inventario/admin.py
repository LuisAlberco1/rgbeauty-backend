from django.contrib import admin
from .models import CategoriaProducto, Marca, Producto, ProductoPrecio


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("id_categoria_producto", "nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("id_marca", "nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)


class ProductoPrecioInline(admin.TabularInline):
    model = ProductoPrecio
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("id_producto", "sku", "nombre", "categoria", "marca", "activo", "fecha_creacion")
    search_fields = ("sku", "nombre", "marca__nombre", "categoria__nombre")
    list_filter = ("activo", "categoria", "marca")
    list_select_related = ("categoria", "marca")
    inlines = (ProductoPrecioInline,)



