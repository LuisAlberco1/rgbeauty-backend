from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("productos/", views.productos_lista, name="productos_lista"),
    path("productos/nuevo/", views.producto_form, name="producto_form"),
    path("productos/<int:id_producto>/editar/", views.producto_form, name="producto_editar"),
    path("productos/<int:id_producto>/desactivar/", views.producto_desactivar, name="producto_desactivar"),
    path("stock/", views.stock_lista, name="stock_lista"),
    path("movimientos/nuevo/", views.movimiento_form, name="movimiento_form"),
    path("ajustes-stock/", views.ajustes_stock, name="ajustes_stock"),
    path("historial/", views.movimientos_historial, name="movimientos_historial"),
]
