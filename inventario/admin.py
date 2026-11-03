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
    list_display = (
        "id_producto",
        "sku",
        "nombre",
        "categoria",
        "marca",
        "creado_por",
        "activo",
        "fecha_creacion",
    )
    search_fields = ("sku", "nombre", "marca__nombre", "categoria__nombre")
    list_filter = ("activo", "categoria", "marca")
    list_select_related = ("categoria", "marca", "creado_por")
    inlines = (ProductoPrecioInline,)
    exclude = ("creado_por",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request, obj)
        return (
            request.user.is_superuser
            or obj.creado_por_id == request.user.pk
            or request.user.has_perm("inventario.change_producto")
        )

    def has_delete_permission(self, request, obj=None):
        return False
