from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cuenta/", views.cuenta, name="cuenta"),
    path("cuenta/contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
    path("cuenta/activar-administradora/", views.activar_cuenta_administradora, name="activar_cuenta_administradora"),
    path("cuenta/accesos/", views.historial_accesos, name="historial_accesos"),
    path("equipo/", views.cuentas_equipo, name="cuentas_equipo"),
    path("equipo/nueva/", views.cuenta_equipo_nueva, name="cuenta_equipo_nueva"),
    path("equipo/<int:user_id>/editar/", views.cuenta_equipo_editar, name="cuenta_equipo_editar"),
    path("equipo/<int:user_id>/estado/", views.cuenta_equipo_cambiar_estado, name="cuenta_equipo_cambiar_estado"),
    path("productos/", views.productos_lista, name="productos_lista"),
    path("mis-productos/", views.mis_productos, name="mis_productos"),
    path("productos/nuevo/", views.producto_form, name="producto_form"),
    path("productos/<int:id_producto>/", views.producto_detalle, name="producto_detalle"),
    path("productos/<int:id_producto>/editar/", views.producto_form, name="producto_editar"),
    path("productos/<int:id_producto>/estado/", views.producto_cambiar_estado, name="producto_cambiar_estado"),
    path("productos/<int:id_producto>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("categorias/nueva/", views.categoria_form, name="categoria_form"),
    path("categorias/<int:id_categoria>/editar/", views.categoria_form, name="categoria_editar"),
    path("categorias/<int:id_categoria>/estado/", views.categoria_cambiar_estado, name="categoria_cambiar_estado"),
    path("categorias/<int:id_categoria>/eliminar/", views.categoria_eliminar, name="categoria_eliminar"),
    path("marcas/", views.marcas_lista, name="marcas_lista"),
    path("marcas/nueva/", views.marca_form, name="marca_form"),
    path("marcas/<int:id_marca>/editar/", views.marca_form, name="marca_editar"),
    path("marcas/<int:id_marca>/estado/", views.marca_cambiar_estado, name="marca_cambiar_estado"),
    path("marcas/<int:id_marca>/eliminar/", views.marca_eliminar, name="marca_eliminar"),
    path("stock/", views.stock_lista, name="stock_lista"),
    path("stock/actual/", views.stock_actual, name="stock_actual"),
    path("movimientos/nuevo/", views.movimiento_form, name="movimiento_form"),
    path("ajustes-stock/", views.ajustes_stock, name="ajustes_stock"),
    path("historial/", views.movimientos_historial, name="movimientos_historial"),
]
