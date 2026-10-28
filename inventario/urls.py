from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("productos/", views.productos_lista, name="productos_lista"),
    path("productos/nuevo/", views.producto_form, name="producto_form"),
    path("productos/<int:id_producto>/editar/", views.producto_form, name="producto_editar"),
    path("productos/<int:id_producto>/desactivar/", views.producto_desactivar, name="producto_desactivar"),
    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("categorias/nueva/", views.categoria_form, name="categoria_form"),
    path("categorias/<int:id_categoria>/editar/", views.categoria_form, name="categoria_editar"),
    path("categorias/<int:id_categoria>/estado/", views.categoria_cambiar_estado, name="categoria_cambiar_estado"),
    path("marcas/", views.marcas_lista, name="marcas_lista"),
    path("marcas/nueva/", views.marca_form, name="marca_form"),
    path("marcas/<int:id_marca>/editar/", views.marca_form, name="marca_editar"),
    path("marcas/<int:id_marca>/estado/", views.marca_cambiar_estado, name="marca_cambiar_estado"),
    path("stock/", views.stock_lista, name="stock_lista"),
    path("movimientos/nuevo/", views.movimiento_form, name="movimiento_form"),
    path("ajustes-stock/", views.ajustes_stock, name="ajustes_stock"),
    path("historial/", views.movimientos_historial, name="movimientos_historial"),
]
