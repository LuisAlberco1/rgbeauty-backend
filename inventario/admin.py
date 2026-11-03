from datetime import timedelta

from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import (
    CategoriaProducto,
    DetalleMovimiento,
    Inventario,
    Marca,
    MovimientoInventario,
    Persona,
    Producto,
    ProductoPrecio,
    Stock,
    TipoMovimiento,
    UsuarioNegocio,
)


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("id_categoria_producto", "nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("id_marca", "nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


class ProductoPrecioInline(admin.TabularInline):
    model = ProductoPrecio
    fields = ("precio", "fecha_inicio", "fecha_fin", "activo")
    readonly_fields = ("fecha_inicio", "fecha_fin", "activo")
    extra = 1
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields
        return self.fields


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
    actions = None

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        if formset.model is not ProductoPrecio:
            return super().save_formset(request, form, formset, change)

        nuevos_precios = [
            precio for precio in formset.save(commit=False) if precio.pk is None
        ]
        if nuevos_precios:
            precio_actual = ProductoPrecio.objects.filter(
                producto=form.instance,
                activo=True,
                fecha_fin__isnull=True,
            ).order_by("-fecha_inicio").first()
            if precio_actual:
                ahora = timezone.now()
                if ahora <= precio_actual.fecha_inicio:
                    ahora = precio_actual.fecha_inicio + timedelta(seconds=1)
                precio_actual.fecha_fin = ahora
                precio_actual.activo = False
                precio_actual.save(update_fields=["fecha_fin", "activo"])

            for precio in nuevos_precios:
                precio.producto = form.instance
                precio.activo = True
                precio.fecha_fin = None
                precio.save()

        formset.save_m2m()

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


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("id_inventario", "nombre", "ubicacion", "activo")
    search_fields = ("nombre", "ubicacion")
    list_filter = ("activo",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TipoMovimiento)
class TipoMovimientoAdmin(admin.ModelAdmin):
    list_display = ("id_tipo_movimiento", "nombre", "afecta_stock")
    search_fields = ("nombre",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("id_persona", "rut", "nombre", "apellido_paterno", "email")
    search_fields = ("rut", "nombre", "apellido_paterno", "email")
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UsuarioNegocio)
class UsuarioNegocioAdmin(admin.ModelAdmin):
    class Form(forms.ModelForm):
        class Meta:
            model = UsuarioNegocio
            fields = ("persona", "nombre_usuario", "activo")
            help_texts = {
                "nombre_usuario": (
                    "Debe coincidir exactamente con el nombre de usuario "
                    "de la cuenta creada en Autenticación > Usuarios."
                ),
            }

        def clean_nombre_usuario(self):
            nombre_usuario = self.cleaned_data["nombre_usuario"].strip()
            if not self.instance.pk and not get_user_model().objects.filter(
                username=nombre_usuario,
                is_active=True,
            ).exists():
                raise forms.ValidationError(
                    "Crea primero esta cuenta en Autenticación > Usuarios."
                )
            return nombre_usuario

    form = Form
    list_display = ("id_usuario", "nombre_usuario", "persona", "activo")
    search_fields = ("nombre_usuario", "persona__rut", "persona__nombre")
    list_filter = ("activo",)
    exclude = ("password_hash",)
    readonly_fields = ("fecha_registro", "ultimo_acceso")
    actions = None

    def save_model(self, request, obj, form, change):
        if not change:
            obj.password_hash = make_password(None)
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False


class SoloLecturaAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductoPrecio)
class ProductoPrecioAdmin(SoloLecturaAdmin):
    list_display = ("id_precio", "producto", "precio", "fecha_inicio", "fecha_fin", "activo")
    list_filter = ("activo",)
    search_fields = ("producto__nombre", "producto__sku")
    list_select_related = ("producto",)


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(SoloLecturaAdmin):
    list_display = ("id_movimiento", "fecha", "inventario", "usuario", "tipo_movimiento", "motivo")
    list_filter = ("tipo_movimiento", "inventario", "fecha")
    search_fields = ("motivo", "usuario__nombre_usuario")
    list_select_related = ("inventario", "usuario", "tipo_movimiento")


@admin.register(DetalleMovimiento)
class DetalleMovimientoAdmin(SoloLecturaAdmin):
    list_display = (
        "id_detalle_movimiento",
        "movimiento",
        "producto",
        "cantidad",
        "stock_anterior",
        "stock_nuevo",
    )
    list_select_related = ("movimiento", "producto")
    search_fields = ("producto__nombre", "producto__sku", "movimiento__motivo")


@admin.register(Stock)
class StockAdmin(SoloLecturaAdmin):
    list_display = ("inventario", "producto", "cantidad_actual", "fecha_actualizacion")
    list_filter = ("inventario",)
    search_fields = ("producto__nombre", "producto__sku", "inventario__nombre")
    list_select_related = ("inventario", "producto")
