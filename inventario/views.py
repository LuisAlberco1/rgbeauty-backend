import logging
from datetime import timedelta
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    AjusteStockForm,
    CategoriaProductoForm,
    CuentaEquipoForm,
    ExistenciasFiltroForm,
    HistorialFiltroForm,
    MarcaForm,
    MovimientoStockForm,
    PerfilForm,
    ProductoForm,
)
from .models import (
    CategoriaProducto,
    DetalleMovimiento,
    Inventario,
    Marca,
    MovimientoInventario,
    Producto,
    ProductoImagen,
    ProductoPrecio,
    RegistroAcceso,
    Stock,
    TipoMovimiento,
)
from .services import (
    LOW_STOCK_THRESHOLD,
    MovimientoStockError,
    clasificar_stock,
    registrar_movimiento_stock,
)
from .roles import ADMIN_GROUP_NAME
from .session_utils import (
    ACCESS_RECORD_SESSION_KEY,
    hash_session_key,
)

logger = logging.getLogger(__name__)


def _delete_product_image_file(file_name):
    if not file_name or not file_name.startswith("productos/"):
        return True
    try:
        default_storage.delete(file_name)
    except OSError:
        logger.exception("No se pudo borrar un archivo de imagen de producto")
        return False
    return True


@login_required
def dashboard(request):
    _verificar_permiso(request.user, "inventario.view_stock")
    dashboard_error = None
    stats = None
    alertas_stock = []
    movimientos_recientes = []

    try:
        stocks_activos = Stock.objects.filter(
            producto__activo=True,
            inventario__activo=True,
        )
        stats = stocks_activos.aggregate(
            productos_activos=Count("producto_id", distinct=True),
            unidades_stock=Coalesce(Sum("cantidad_actual"), 0),
            productos_stock_bajo=Count(
                "producto_id",
                filter=Q(
                    cantidad_actual__gt=0,
                    cantidad_actual__lte=LOW_STOCK_THRESHOLD,
                ),
            ),
            productos_agotados=Count(
                "producto_id",
                filter=Q(cantidad_actual=0),
            ),
        )
        alertas_stock = list(
            stocks_activos.select_related("producto", "inventario")
            .filter(cantidad_actual__lte=LOW_STOCK_THRESHOLD)
            .order_by("cantidad_actual", "producto__nombre", "inventario__nombre")[:5]
        )
        if request.user.has_perm("inventario.view_movimientoinventario"):
            movimientos_recientes = list(
                DetalleMovimiento.objects.select_related(
                    "producto",
                    "movimiento__tipo_movimiento",
                ).order_by(
                    "-movimiento__fecha",
                    "-movimiento__id_movimiento",
                    "-id_detalle_movimiento",
                )[:5]
            )
    except DatabaseError:
        logger.exception("Error cargando los indicadores del dashboard")
        dashboard_error = (
            "No se pudieron cargar los datos del inventario. "
            "Comprueba la conexión y las tablas de MySQL."
        )

    context = {
        "dashboard_error": dashboard_error,
        "productos_activos": stats["productos_activos"] if stats else None,
        "unidades_stock": stats["unidades_stock"] if stats else None,
        "productos_stock_bajo": stats["productos_stock_bajo"] if stats else None,
        "productos_agotados": stats["productos_agotados"] if stats else None,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "alertas_stock": alertas_stock,
        "movimientos_recientes": movimientos_recientes,
    }
    return render(request, "dashboard/index.html", context)


@login_required
def cuenta(request):
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Los datos de tu cuenta se actualizaron correctamente.")
            return redirect("inventario:cuenta")
    else:
        form = PerfilForm(instance=request.user)

    return render(request, "inventario/cuenta.html", {
        "form": form,
        "rol_cuenta": (
            "Cuenta técnica"
            if request.user.is_superuser
            else "Administradora"
            if _es_administradora(request.user)
            else "Asistenta"
        ),
        "puede_administrar_cuentas": _es_administradora(request.user),
        "puede_ver_historial_accesos": (
            request.user.is_superuser
            or request.user.has_perm("inventario.view_access_history")
        ),
        "puede_activar_cuenta_administradora": request.user.is_superuser,
        "cuentas_activas": (
            get_user_model().objects.filter(is_active=True, is_superuser=False).count()
            if _es_administradora(request.user)
            else None
        ),
    })


@login_required
def cambiar_contrasena(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.save()
            update_session_auth_hash(request, usuario)
            session_key = request.session.session_key
            if session_key:
                RegistroAcceso.objects.filter(
                    pk=request.session.get(ACCESS_RECORD_SESSION_KEY),
                    usuario=usuario,
                    cierre__isnull=True,
                ).update(clave_sesion_hash=hash_session_key(session_key))
            messages.success(request, "Tu contraseña se actualizó correctamente.")
            return redirect("inventario:cuenta")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "inventario/cambiar_contrasena.html", {"form": form})


def _verificar_duena(usuario):
    _verificar_permiso(usuario, "inventario.manage_team_accounts")


def _es_administradora(usuario):
    return (
        usuario.is_superuser
        or usuario.has_perm("inventario.manage_team_accounts")
    )


def _es_cuenta_administradora(usuario):
    return usuario.groups.filter(name=ADMIN_GROUP_NAME).exists()


def _hay_otra_administradora_activa(excluir_usuario_id):
    return get_user_model().objects.filter(
        is_active=True,
        is_superuser=False,
        groups__name=ADMIN_GROUP_NAME,
    ).exclude(pk=excluir_usuario_id).exists()


def _verificar_permiso(usuario, permission):
    if not usuario.is_superuser and not usuario.has_perm(permission):
        raise PermissionDenied


@login_required
@require_POST
def activar_cuenta_administradora(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    try:
        grupo = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist as exc:
        messages.error(
            request,
            "Los roles no están configurados. Pide al administrador técnico que "
            "ejecute setup_inventory.",
        )
        return redirect("inventario:cuenta")
    if not grupo.permissions.filter(
        content_type__app_label="inventario",
        codename="manage_team_accounts",
    ).exists():
        messages.error(
            request,
            "El rol Administradora no tiene sus permisos configurados. "
            "Ejecuta setup_inventory antes de continuar.",
        )
        return redirect("inventario:cuenta")
    if grupo.permissions.count() < Permission.objects.filter(
        content_type__app_label="inventario",
    ).count():
        messages.error(
            request,
            "El rol Administradora está incompleto. Ejecuta setup_inventory "
            "antes de continuar.",
        )
        return redirect("inventario:cuenta")
    request.user.groups.add(grupo)
    request.user.is_superuser = False
    request.user.is_staff = False
    request.user.save(update_fields=["is_superuser", "is_staff"])
    messages.success(
        request,
        "Tu cuenta ahora es Administradora de la aplicación. "
        "Ya no necesita acceso a Django Admin.",
    )
    return redirect("inventario:cuenta")


@login_required
def cuentas_equipo(request):
    _verificar_duena(request.user)
    User = get_user_model()
    cuentas = User.objects.filter(is_superuser=False).prefetch_related("groups").order_by("username")
    return render(request, "inventario/cuentas_equipo.html", {"cuentas": cuentas})


@login_required
def historial_accesos(request):
    _verificar_permiso(request.user, "inventario.view_access_history")
    eventos = Paginator(
        RegistroAcceso.objects.select_related("usuario"),
        50,
    ).get_page(request.GET.get("page"))
    sesiones_vigentes = {
        hash_session_key(session_key)
        for session_key in Session.objects.filter(
            expire_date__gt=timezone.now(),
        ).values_list("session_key", flat=True)
    }
    for evento in eventos:
        evento.sesion_activa = (
            evento.cierre is None
            and evento.clave_sesion_hash in sesiones_vigentes
            and evento.usuario is not None
            and evento.usuario.is_active
        )
    return render(request, "inventario/historial_accesos.html", {
        "eventos": eventos,
        "sesiones_activas": sum(evento.sesion_activa for evento in eventos),
    })


@login_required
def cuenta_equipo_nueva(request):
    _verificar_duena(request.user)
    if request.method == "POST":
        form = CuentaEquipoForm(request.POST)
        if form.is_valid():
            cuenta = form.save()
            messages.success(request, f"La cuenta «{cuenta.username}» fue creada.")
            return redirect("inventario:cuentas_equipo")
    else:
        form = CuentaEquipoForm()

    return render(request, "inventario/cuenta_equipo_form.html", {
        "form": form,
        "titulo": "Crear cuenta del equipo",
    })


@login_required
def cuenta_equipo_editar(request, user_id):
    _verificar_duena(request.user)
    User = get_user_model()
    cuenta = get_object_or_404(User, pk=user_id, is_superuser=False)
    if request.method == "POST":
        form = CuentaEquipoForm(request.POST, instance=cuenta)
        if form.is_valid():
            loses_last_admin = (
                cuenta.is_active
                and _es_cuenta_administradora(cuenta)
                and form.cleaned_data["role"] != ADMIN_GROUP_NAME
                and not _hay_otra_administradora_activa(cuenta.pk)
            )
            if loses_last_admin:
                form.add_error(
                    "role",
                    "No puedes quitar el rol a la última Administradora activa. "
                    "Crea otra cuenta Administradora primero.",
                )
            else:
                form.save()
                messages.success(request, f"La cuenta «{cuenta.username}» fue actualizada.")
                return redirect("inventario:cuentas_equipo")
    else:
        form = CuentaEquipoForm(instance=cuenta)

    return render(request, "inventario/cuenta_equipo_form.html", {
        "form": form,
        "cuenta": cuenta,
        "titulo": "Editar cuenta del equipo",
    })


@login_required
@require_POST
def cuenta_equipo_cambiar_estado(request, user_id):
    _verificar_duena(request.user)
    User = get_user_model()
    cuenta = get_object_or_404(User, pk=user_id, is_superuser=False)
    if cuenta.pk == request.user.pk and cuenta.is_active:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
        return redirect("inventario:cuentas_equipo")
    if (
        cuenta.is_active
        and _es_cuenta_administradora(cuenta)
        and not _hay_otra_administradora_activa(cuenta.pk)
    ):
        messages.error(
            request,
            "No puedes desactivar a la última Administradora activa. "
            "Crea otra cuenta Administradora primero.",
        )
        return redirect("inventario:cuentas_equipo")
    cuenta.is_active = not cuenta.is_active
    cuenta.save(update_fields=["is_active"])
    estado = "activada" if cuenta.is_active else "desactivada"
    messages.success(request, f"La cuenta «{cuenta.username}» fue {estado}.")
    return redirect("inventario:cuentas_equipo")


def _productos_lista(request):
    buscar = request.GET.get("buscar", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    marca_id = request.GET.get("marca", "").strip()
    estado = request.GET.get("estado", "").strip()

    productos = Producto.objects.select_related(
        "categoria",
        "marca",
        "creado_por",
    ).prefetch_related(
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
        productos = productos.filter(activo=True, archivado=False)
    elif estado == "inactivo":
        productos = productos.filter(activo=False, archivado=False)
    elif estado == "archivado":
        productos = productos.filter(archivado=True)
    else:
        productos = productos.filter(archivado=False)

    categorias = CategoriaProducto.objects.filter(activo=True).order_by("nombre")
    marcas = Marca.objects.all().order_by("nombre")
    page_obj = Paginator(productos.order_by("nombre"), 10).get_page(
        request.GET.get("page", 1)
    )
    filter_params = request.GET.copy()
    filter_params.pop("page", None)
    return render(request, "inventario/productos_lista.html", {
        "page_obj": page_obj,
        "categorias": categorias,
        "marcas": marcas,
        "buscar": buscar,
        "categoria_seleccionada": categoria_id,
        "marca_seleccionada": marca_id,
        "estado_seleccionado": estado,
        "filter_query": filter_params.urlencode(),
    })


@login_required
def productos_lista(request):
    _verificar_permiso(request.user, "inventario.view_producto")
    return _productos_lista(request)


@login_required
def mis_productos(request):
    return redirect("inventario:productos_lista")


@login_required
def producto_detalle(request, id_producto):
    _verificar_permiso(request.user, "inventario.view_producto")
    producto = get_object_or_404(
        Producto.objects.select_related(
            "categoria",
            "marca",
            "creado_por",
        ).prefetch_related(
            Prefetch(
                "precios",
                queryset=ProductoPrecio.objects.order_by("-fecha_inicio"),
            ),
            Prefetch(
                "imagenes",
                queryset=ProductoImagen.objects.filter(
                    activo=True,
                    principal=True,
                ).order_by("orden"),
            ),
        ),
        pk=id_producto,
    )
    precios = list(producto.precios.all())
    imagen_producto = next(iter(producto.imagenes.all()), None)
    puede_ver_existencias = (
        request.user.is_superuser
        or request.user.has_perm("inventario.view_stock")
    )
    precio_actual = next(
        (
            precio
            for precio in precios
            if precio.activo and precio.fecha_fin is None
        ),
        None,
    )
    existencias = (
        list(
            Stock.objects.filter(
                producto=producto,
                inventario__activo=True,
            ).select_related("inventario").order_by("inventario__nombre")
        )
        if puede_ver_existencias
        else []
    )
    return render(request, "inventario/producto_detalle.html", {
        "producto": producto,
        "imagen_producto": imagen_producto,
        "precio_actual": precio_actual,
        "precios": precios,
        "existencias": existencias,
        "stock_total": sum(existencia.cantidad_actual for existencia in existencias),
        "puede_ver_existencias": puede_ver_existencias,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "puede_editar": _puede_editar_producto(request.user),
        "puede_registrar_movimiento": (
            request.user.is_superuser
            or request.user.has_perm("inventario.register_stock_movement")
        ),
    })


def _puede_editar_producto(usuario):
    return (
        usuario.is_superuser
        or usuario.has_perm("inventario.change_producto")
    )


def _verificar_permiso_producto(usuario):
    if not _puede_editar_producto(usuario):
        raise PermissionDenied


@login_required
def producto_form(request, id_producto=None):
    producto = get_object_or_404(Producto, pk=id_producto) if id_producto is not None else None
    if producto is not None:
        _verificar_permiso_producto(request.user)
        if producto.archivado:
            raise PermissionDenied
    else:
        _verificar_permiso(request.user, "inventario.add_producto")

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            nuevo_archivo = None
            archivo_anterior = None
            try:
                with transaction.atomic():
                    producto_guardado = form.save(commit=False)
                    if producto is None:
                        producto_guardado.activo = True
                        producto_guardado.creado_por = request.user
                    producto_guardado.save()

                    imagen_anterior = ProductoImagen.objects.filter(
                        producto=producto_guardado,
                        orden=1,
                    ).first()
                    imagen_subida = form.cleaned_data.get("imagen")
                    quitar_imagen = form.cleaned_data.get("eliminar_imagen")

                    if imagen_subida:
                        extension = {
                            "JPEG": ".jpg",
                            "PNG": ".png",
                            "WEBP": ".webp",
                        }[imagen_subida.image.format]
                        nuevo_archivo = default_storage.save(
                            f"productos/{uuid4().hex}{extension}",
                            imagen_subida,
                        )
                        if imagen_anterior:
                            archivo_anterior = imagen_anterior.url
                            imagen_anterior.url = nuevo_archivo
                            imagen_anterior.texto_alternativo = producto_guardado.nombre
                            imagen_anterior.principal = True
                            imagen_anterior.activo = True
                            imagen_anterior.save(update_fields=[
                                "url",
                                "texto_alternativo",
                                "principal",
                                "activo",
                            ])
                        else:
                            ProductoImagen.objects.create(
                                producto=producto_guardado,
                                url=nuevo_archivo,
                                texto_alternativo=producto_guardado.nombre,
                                orden=1,
                                principal=True,
                                activo=True,
                            )
                    elif quitar_imagen and imagen_anterior:
                        archivo_anterior = imagen_anterior.url
                        imagen_anterior.delete()

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
                if archivo_anterior and archivo_anterior != nuevo_archivo:
                    if not _delete_product_image_file(archivo_anterior):
                        messages.warning(
                            request,
                            "El producto se guardó, pero no se pudo borrar el archivo de imagen anterior.",
                        )
                messages.success(request, "Producto guardado correctamente.")
                return redirect("inventario:productos_lista")
            except IntegrityError:
                if nuevo_archivo:
                    _delete_product_image_file(nuevo_archivo)
                form.add_error("sku", "El SKU ya existe o hay una restricción de la base de datos que impide guardar el producto.")
            except Exception:
                if nuevo_archivo:
                    _delete_product_image_file(nuevo_archivo)
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
def producto_cambiar_estado(request, id_producto):
    _verificar_permiso_producto(request.user)
    producto = get_object_or_404(Producto, pk=id_producto, archivado=False)
    producto.activo = not producto.activo
    producto.save(update_fields=["activo"])
    if producto.activo:
        messages.success(request, f"El producto {producto.nombre} fue activado.")
    else:
        messages.success(
            request,
            f"El producto {producto.nombre} fue desactivado. Se conservaron sus registros.",
        )
    return redirect("inventario:productos_lista")


@login_required
@require_POST
def producto_eliminar(request, id_producto):
    _verificar_permiso(request.user, "inventario.delete_producto")
    with transaction.atomic():
        producto = get_object_or_404(
            Producto.objects.select_for_update(),
            pk=id_producto,
            archivado=False,
        )
        if producto.activo:
            messages.error(
                request,
                "Desactiva el producto antes de eliminarlo del catálogo.",
            )
            return redirect("inventario:productos_lista")
        nombre = producto.nombre
        producto.archivado = True
        producto.save(update_fields=["archivado"])
    messages.success(
        request,
        f"El producto {nombre} fue retirado definitivamente del catálogo. "
        "Se conservaron sus existencias y todo su historial.",
    )
    return redirect("inventario:productos_lista")


@login_required
def categorias_lista(request):
    _verificar_permiso(request.user, "inventario.view_categoriaproducto")
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
    _verificar_permiso(
        request.user,
        "inventario.add_categoriaproducto"
        if categoria is None
        else "inventario.change_categoriaproducto",
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
    _verificar_permiso(request.user, "inventario.change_categoriaproducto")
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
@require_POST
def categoria_eliminar(request, id_categoria):
    _verificar_permiso(request.user, "inventario.delete_categoriaproducto")
    categoria = get_object_or_404(CategoriaProducto, pk=id_categoria)
    nombre = categoria.nombre
    try:
        categoria.delete()
    except ProtectedError:
        messages.error(
            request,
            f"No se puede eliminar la categoría {nombre} porque tiene productos asociados. "
            "Desactívala para conservar el historial.",
        )
    else:
        messages.success(request, f"La categoría {nombre} fue eliminada.")
    return redirect("inventario:categorias_lista")


@login_required
def marcas_lista(request):
    _verificar_permiso(request.user, "inventario.view_marca")
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
    _verificar_permiso(
        request.user,
        "inventario.add_marca" if marca is None else "inventario.change_marca",
    )

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
    _verificar_permiso(request.user, "inventario.change_marca")
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
@require_POST
def marca_eliminar(request, id_marca):
    _verificar_permiso(request.user, "inventario.delete_marca")
    marca = get_object_or_404(Marca, pk=id_marca)
    nombre = marca.nombre
    try:
        marca.delete()
    except ProtectedError:
        messages.error(
            request,
            f"No se puede eliminar la marca {nombre} porque tiene productos asociados. "
            "Desactívala para conservar el historial.",
        )
    else:
        messages.success(request, f"La marca {nombre} fue eliminada.")
    return redirect("inventario:marcas_lista")


@login_required
def stock_lista(request):
    _verificar_permiso(request.user, "inventario.view_stock")
    form = ExistenciasFiltroForm(request.GET)
    stock_rows = []
    stock_stats = None
    error = None
    current_page = 1
    total_pages = 1

    try:
        if form.is_valid():
            stocks = Stock.objects.filter(
                producto__activo=True,
                inventario__activo=True,
            ).select_related("producto__categoria", "inventario")
            buscar = form.cleaned_data["buscar"]
            inventario = form.cleaned_data["inventario"]
            estado = form.cleaned_data["estado"]

            if buscar:
                stocks = stocks.filter(
                    Q(producto__nombre__icontains=buscar)
                    | Q(producto__sku__icontains=buscar)
                )
            if inventario:
                stocks = stocks.filter(inventario=inventario)
            if estado == "agotado":
                stocks = stocks.filter(cantidad_actual=0)
            elif estado == "bajo":
                stocks = stocks.filter(
                    cantidad_actual__gt=0,
                    cantidad_actual__lte=LOW_STOCK_THRESHOLD,
                )
            elif estado == "disponible":
                stocks = stocks.filter(cantidad_actual__gt=LOW_STOCK_THRESHOLD)

            stock_stats = stocks.aggregate(
                productos=Count("producto_id", distinct=True),
                unidades=Coalesce(Sum("cantidad_actual"), 0),
                stock_bajo=Count(
                    "producto_id",
                    filter=Q(
                        cantidad_actual__gt=0,
                        cantidad_actual__lte=LOW_STOCK_THRESHOLD,
                    ),
                ),
                agotados=Count(
                    "producto_id",
                    filter=Q(cantidad_actual=0),
                ),
                total_filas=Count("producto_id"),
            )
            page_obj = Paginator(
                stocks.order_by("inventario__nombre", "producto__nombre"),
                25,
            ).get_page(request.GET.get("page", "1"))
            current_page = page_obj.number
            total_pages = page_obj.paginator.num_pages
            stock_rows = list(page_obj.object_list)
            for row in stock_rows:
                row.estado_stock = clasificar_stock(row.cantidad_actual)
    except DatabaseError:
        logger.exception("Error consultando las existencias")
        error = (
            "No se pudieron consultar las existencias. "
            "Comprueba la conexión y las tablas de MySQL."
        )

    filter_params = request.GET.copy()
    filter_params.pop("page", None)
    return render(request, "inventario/stock_lista.html", {
        "form": form,
        "stock_rows": stock_rows,
        "stock_stats": stock_stats,
        "error": error,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "current_page": current_page,
        "total_pages": total_pages,
        "filter_query": filter_params.urlencode(),
    })


@login_required
@require_GET
def stock_actual(request):
    _verificar_permiso(request.user, "inventario.view_stock")
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
        cantidad_actual = Stock.objects.filter(
            inventario_id=inventario_id,
            producto_id=producto_id,
        ).values_list("cantidad_actual", flat=True).first()
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

    return JsonResponse({"stock": cantidad_actual if cantidad_actual is not None else 0})


@login_required
def movimiento_form(request):
    _verificar_permiso(request.user, "inventario.register_stock_movement")
    configuracion_lista = False
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
                    usuario=request.user,
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
        initial = {}
        producto_id = request.GET.get("producto", "").strip()
        if producto_id.isdigit():
            initial["producto"] = producto_id
        form = MovimientoStockForm(initial=initial)
        configuracion_lista = (
            form.fields["inventario"].queryset.exists()
            and form.fields["producto"].queryset.exists()
            and form.fields["tipo_movimiento"].queryset.count() == 2
        )

    return render(request, "inventario/movimiento_form.html", {
        "form": form,
        "configuracion_lista": configuracion_lista,
    })


@login_required
def ajustes_stock(request):
    _verificar_permiso(request.user, "inventario.adjust_stock")
    configuracion_lista = False
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
                    usuario=request.user,
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
    })


@login_required
def movimientos_historial(request):
    _verificar_permiso(request.user, "inventario.view_movimientoinventario")
    form = HistorialFiltroForm(request.GET)
    error = None
    page_obj = None
    total_movimientos = entradas = salidas = ajustes = None

    try:
        if form.is_valid():
            movimientos = MovimientoInventario.objects.all()
            producto = form.cleaned_data["producto"]
            tipo = form.cleaned_data["tipo"]
            desde = form.cleaned_data["desde"]
            hasta = form.cleaned_data["hasta"]

            if producto:
                movimientos = movimientos.filter(detalles__producto=producto)
            if tipo:
                movimientos = movimientos.filter(tipo_movimiento__nombre=tipo)
            if desde:
                movimientos = movimientos.filter(fecha__date__gte=desde)
            if hasta:
                movimientos = movimientos.filter(fecha__date__lte=hasta)
            movimientos = movimientos.distinct()

            total_movimientos = movimientos.count()
            entradas = movimientos.filter(tipo_movimiento__nombre="Entrada").count()
            salidas = movimientos.filter(tipo_movimiento__nombre="Salida").count()
            ajustes = movimientos.filter(tipo_movimiento__nombre="Ajuste").count()

            detalles = DetalleMovimiento.objects.filter(movimiento__in=movimientos)
            if producto:
                detalles = detalles.filter(producto=producto)
            detalles = detalles.select_related(
                "producto",
                "movimiento__inventario",
                "movimiento__tipo_movimiento",
                "movimiento__usuario",
            ).order_by(
                "-movimiento__fecha",
                "-movimiento__id_movimiento",
                "-id_detalle_movimiento",
            )
            page_obj = Paginator(detalles, 25).get_page(request.GET.get("page", 1))
    except DatabaseError:
        logger.exception("Error consultando el historial de movimientos")
        error = (
            "No se pudo consultar el historial. "
            "Comprueba la conexión y las tablas de MySQL."
        )

    filter_params = request.GET.copy()
    filter_params.pop("page", None)
    return render(request, "inventario/movimientos_historial.html", {
        "form": form,
        "error": error,
        "page_obj": page_obj,
        "total_movimientos": total_movimientos,
        "entradas": entradas,
        "salidas": salidas,
        "ajustes": ajustes,
        "filter_query": filter_params.urlencode(),
    })
 
