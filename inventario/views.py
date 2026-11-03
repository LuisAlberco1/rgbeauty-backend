import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    AjusteStockForm,
    CategoriaProductoForm,
    MarcaForm,
    MovimientoStockForm,
    ProductoForm,
)
from .models import (
    CategoriaProducto,
    Inventario,
    Marca,
    Producto,
    ProductoPrecio,
    TipoMovimiento,
    UsuarioNegocio,
)
from .services import MovimientoStockError, registrar_movimiento_stock

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    return render(request, "dashboard/index.html")


@login_required
def productos_lista(request):
    buscar = request.GET.get("buscar", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    marca_id = request.GET.get("marca", "").strip()
    estado = request.GET.get("estado", "").strip()

    productos = Producto.objects.select_related("categoria", "marca").prefetch_related(
        Prefetch("precios", queryset=ProductoPrecio.objects.order_by("-fecha_inicio"))
    )

    if buscar:
        productos = productos.filter(
            Q(nombre__icontains=buscar)
            | Q(sku__icontains=buscar)
            | Q(marca__nombre__icontains=buscar)
            | Q(categoria__nombre__icontains=buscar)
        )
    if categoria_id:
        if categoria_id.isdigit():
            productos = productos.filter(categoria_id=int(categoria_id))
        else:
            productos = productos.none()
    if marca_id:
        if marca_id.isdigit():
            productos = productos.filter(marca_id=int(marca_id))
        else:
            productos = productos.none()
    if estado == "activo":
        productos = productos.filter(activo=True)
    elif estado == "inactivo":
        productos = productos.filter(activo=False)

    categorias = CategoriaProducto.objects.filter(activo=True).order_by("nombre")
    marcas = Marca.objects.all().order_by("nombre")
    return render(request, "inventario/productos_lista.html", {
        "productos": productos.order_by("nombre"),
        "categorias": categorias,
        "marcas": marcas,
        "buscar": buscar,
        "categoria_seleccionada": categoria_id,
        "marca_seleccionada": marca_id,
        "estado_seleccionado": estado,
    })


@login_required
def producto_form(request, id_producto=None):
    producto = get_object_or_404(Producto, pk=id_producto) if id_producto is not None else None

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            try:
                with transaction.atomic():
                    producto_guardado = form.save(commit=False)
                    if producto is None:
                        producto_guardado.activo = True
                    producto_guardado.save()

                    nuevo_precio = form.cleaned_data["precio"]
                    precio_actual = ProductoPrecio.objects.filter(
                        producto=producto_guardado,
                        activo=True,
                        fecha_fin__isnull=True,
                    ).order_by("-fecha_inicio").first()

                    if precio_actual is None or precio_actual.precio != nuevo_precio:
                        if precio_actual:
                            ahora = timezone.now()
                            # Asegura que fecha_fin sea posterior a fecha_inicio incluso con precisión de segundos.
                            if precio_actual.fecha_inicio and ahora <= precio_actual.fecha_inicio:
                                ahora = precio_actual.fecha_inicio + timedelta(seconds=1)
                            precio_actual.fecha_fin = ahora
                            precio_actual.activo = False
                            precio_actual.save(update_fields=["fecha_fin", "activo"])
                        ProductoPrecio.objects.create(
                            producto=producto_guardado,
                            precio=nuevo_precio,
                            activo=True,
                        )
                messages.success(request, "Producto guardado correctamente.")
                return redirect("inventario:productos_lista")
            except IntegrityError:
                form.add_error("sku", "El SKU ya existe o hay una restricción de la base de datos que impide guardar el producto.")
            except Exception:
                logger.exception("Error guardando producto")
                messages.error(request, "No se pudo guardar el producto. Comprueba la conexión y las tablas de MySQL.")
    else:
        form = ProductoForm(instance=producto)

    return render(request, "inventario/producto_form.html", {
        "form": form,
        "producto": producto,
        "titulo": "Editar producto" if producto else "Registrar producto",
    })


@login_required
@require_POST
def producto_desactivar(request, id_producto):
    producto = get_object_or_404(Producto, pk=id_producto)
    if producto.activo:
        producto.activo = False
        producto.save(update_fields=["activo"])
        messages.success(request, f"El producto {producto.nombre} fue desactivado. No se eliminó de la base de datos.")
    else:
        messages.info(request, "El producto ya estaba desactivado.")
    return redirect("inventario:productos_lista")


@login_required
def categorias_lista(request):
    buscar = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "").strip()
    categorias = CategoriaProducto.objects.all()

    if buscar:
        categorias = categorias.filter(
            Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar)
        )
    if estado == "activo":
        categorias = categorias.filter(activo=True)
    elif estado == "inactivo":
        categorias = categorias.filter(activo=False)

    return render(request, "inventario/categorias_lista.html", {
        "categorias": categorias.order_by("nombre"),
        "buscar": buscar,
        "estado_seleccionado": estado,
    })


@login_required
def categoria_form(request, id_categoria=None):
    categoria = (
        get_object_or_404(CategoriaProducto, pk=id_categoria)
        if id_categoria is not None
        else None
    )

    if request.method == "POST":
        form = CategoriaProductoForm(request.POST, instance=categoria)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, "Categoría guardada correctamente.")
                return redirect("inventario:categorias_lista")
            except IntegrityError:
                form.add_error("nombre", "Ya existe una categoría con ese nombre.")
    else:
        form = CategoriaProductoForm(instance=categoria)

    return render(request, "inventario/categoria_form.html", {
        "form": form,
        "categoria": categoria,
        "titulo": "Editar categoría" if categoria else "Registrar categoría",
    })


@login_required
@require_POST
def categoria_cambiar_estado(request, id_categoria):
    categoria = get_object_or_404(CategoriaProducto, pk=id_categoria)
    categoria.activo = not categoria.activo
    categoria.save(update_fields=["activo"])

    if categoria.activo:
        messages.success(request, f"La categoría {categoria.nombre} fue activada.")
    else:
        messages.success(
            request,
            f"La categoría {categoria.nombre} fue desactivada. Sus productos y registros se conservaron.",
        )
    return redirect("inventario:categorias_lista")


@login_required
def marcas_lista(request):
    buscar = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "").strip()
    marcas = Marca.objects.all()

    if buscar:
        marcas = marcas.filter(Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar))
    if estado == "activo":
        marcas = marcas.filter(activo=True)
    elif estado == "inactivo":
        marcas = marcas.filter(activo=False)

    return render(request, "inventario/marcas_lista.html", {
        "marcas": marcas.order_by("nombre"),
        "buscar": buscar,
        "estado_seleccionado": estado,
    })


@login_required
def marca_form(request, id_marca=None):
    marca = get_object_or_404(Marca, pk=id_marca) if id_marca is not None else None

    if request.method == "POST":
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, "Marca guardada correctamente.")
                return redirect("inventario:marcas_lista")
            except IntegrityError:
                form.add_error("nombre", "Ya existe una marca con ese nombre.")
    else:
        form = MarcaForm(instance=marca)

    return render(request, "inventario/marca_form.html", {
        "form": form,
        "marca": marca,
        "titulo": "Editar marca" if marca else "Registrar marca",
    })


@login_required
@require_POST
def marca_cambiar_estado(request, id_marca):
    marca = get_object_or_404(Marca, pk=id_marca)
    marca.activo = not marca.activo
    marca.save(update_fields=["activo"])

    if marca.activo:
        messages.success(request, f"La marca {marca.nombre} fue activada.")
    else:
        messages.success(
            request,
            f"La marca {marca.nombre} fue desactivada. Sus productos y registros se conservaron.",
        )
    return redirect("inventario:marcas_lista")


@login_required
def stock_lista(request):
    return render(request, "inventario/stock_lista.html")


@login_required
@require_GET
def stock_actual(request):
    try:
        inventario_id = int(request.GET.get("inventario", ""))
        producto_id = int(request.GET.get("producto", ""))
        if inventario_id <= 0 or producto_id <= 0:
            raise ValueError
    except ValueError:
        return JsonResponse(
            {"error": "Selecciona un inventario y un producto válidos."},
            status=400,
        )

    try:
        Inventario.objects.only("pk").get(pk=inventario_id, activo=True)
        Producto.objects.only("pk").get(pk=producto_id, activo=True)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cantidad_actual
                FROM stock
                WHERE id_inventario = %s AND id_producto = %s
                """,
                [inventario_id, producto_id],
            )
            fila_stock = cursor.fetchone()
    except (Inventario.DoesNotExist, Producto.DoesNotExist):
        return JsonResponse(
            {"error": "El inventario o el producto seleccionado ya no está activo."},
            status=404,
        )
    except DatabaseError:
        logger.exception("Error consultando stock actual")
        return JsonResponse(
            {"error": "No se pudo consultar el stock. Comprueba la conexión y las tablas de MySQL."},
            status=503,
        )

    return JsonResponse({"stock": int(fila_stock[0]) if fila_stock else 0})


@login_required
def movimiento_form(request):
    configuracion_lista = False
    responsable_configurado = UsuarioNegocio.objects.filter(
        nombre_usuario=request.user.get_username(),
        activo=True,
    ).exists()
    if request.method == "POST":
        form = MovimientoStockForm(request.POST)
        configuracion_lista = (
            form.fields["inventario"].queryset.exists()
            and form.fields["producto"].queryset.exists()
            and form.fields["tipo_movimiento"].queryset.count() == 2
        )
        if form.is_valid():
            try:
                resultado = registrar_movimiento_stock(
                    inventario_id=form.cleaned_data["inventario"].pk,
                    producto_id=form.cleaned_data["producto"].pk,
                    tipo=form.cleaned_data["tipo_movimiento"].nombre,
                    cantidad=form.cleaned_data["cantidad"],
                    motivo=form.cleaned_data["motivo"],
                    observacion=form.cleaned_data["observacion"],
                    nombre_usuario=request.user.get_username(),
                )
            except MovimientoStockError as exc:
                form.add_error(None, str(exc))
            except DatabaseError:
                logger.exception("Error registrando movimiento de stock")
                form.add_error(
                    None,
                    "No se pudo registrar el movimiento. Comprueba la conexión y las tablas de MySQL.",
                )
            else:
                messages.success(
                    request,
                    f"Movimiento registrado. Stock actualizado de "
                    f"{resultado.stock_anterior} a {resultado.stock_nuevo} unidades.",
                )
                return redirect("inventario:movimiento_form")
    else:
        form = MovimientoStockForm()
        configuracion_lista = (
            form.fields["inventario"].queryset.exists()
            and form.fields["producto"].queryset.exists()
            and form.fields["tipo_movimiento"].queryset.count() == 2
        )

    return render(request, "inventario/movimiento_form.html", {
        "form": form,
        "configuracion_lista": configuracion_lista,
        "responsable_configurado": responsable_configurado,
    })


@login_required
def ajustes_stock(request):
    configuracion_lista = False
    responsable_configurado = UsuarioNegocio.objects.filter(
        nombre_usuario=request.user.get_username(),
        activo=True,
    ).exists()
    if request.method == "POST":
        form = AjusteStockForm(request.POST)
        configuracion_lista = (
            form.fields["inventario"].queryset.exists()
            and form.fields["producto"].queryset.exists()
            and TipoMovimiento.objects.filter(nombre="Ajuste", afecta_stock=True).exists()
        )
        if form.is_valid():
            try:
                resultado = registrar_movimiento_stock(
                    inventario_id=form.cleaned_data["inventario"].pk,
                    producto_id=form.cleaned_data["producto"].pk,
                    tipo="Ajuste",
                    cantidad=form.cleaned_data["cantidad"],
                    motivo=form.cleaned_data["motivo"],
                    observacion=form.cleaned_data["observacion"],
                    nombre_usuario=request.user.get_username(),
                )
            except MovimientoStockError as exc:
                form.add_error(None, str(exc))
            except DatabaseError:
                logger.exception("Error registrando ajuste de stock")
                form.add_error(
                    None,
                    "No se pudo registrar el ajuste. Comprueba la conexión y las tablas de MySQL.",
                )
            else:
                if resultado.movimiento is None:
                    messages.info(request, "El stock ya coincide con el conteo físico; no se registró ningún ajuste.")
                    return redirect("inventario:ajustes_stock")
                else:
                    messages.success(
                        request,
                        f"Ajuste registrado. Stock actualizado de "
                        f"{resultado.stock_anterior} a {resultado.stock_nuevo} unidades.",
                    )
                    return redirect("inventario:ajustes_stock")
    else:
        form = AjusteStockForm()
        configuracion_lista = (
            form.fields["inventario"].queryset.exists()
            and form.fields["producto"].queryset.exists()
            and TipoMovimiento.objects.filter(nombre="Ajuste", afecta_stock=True).exists()
        )

    return render(request, "inventario/ajustes_stock.html", {
        "form": form,
        "configuracion_lista": configuracion_lista,
        "responsable_configurado": responsable_configurado,
    })


@login_required
def movimientos_historial(request):
    return render(request, "inventario/movimientos_historial.html")
