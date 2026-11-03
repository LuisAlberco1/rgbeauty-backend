from django import forms
from .models import (
    CategoriaProducto,
    Inventario,
    Marca,
    Producto,
    ProductoPrecio,
    TipoMovimiento,
)
from .services import LOW_STOCK_THRESHOLD, MAX_STOCK


class ProductoForm(forms.ModelForm):
    precio = forms.DecimalField(
        label="Precio",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
    )

    class Meta:
        model = Producto
        fields = ["sku", "nombre", "descripcion", "categoria", "marca"]
        labels = {
            "sku": "Código SKU",
            "nombre": "Nombre del producto",
            "descripcion": "Descripción",
            "categoria": "Categoría",
            "marca": "Marca",
        }
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control", "maxlength": "50", "required": True}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "maxlength": "150", "required": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categoria": forms.Select(attrs={"class": "form-control", "required": True}),
            "marca": forms.Select(attrs={"class": "form-control", "required": True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = CategoriaProducto.objects.filter(activo=True)
        marcas = Marca.objects.filter(activo=True)
        if self.instance and self.instance.pk:
            categorias = categorias | CategoriaProducto.objects.filter(pk=self.instance.categoria_id)
            marcas = marcas | Marca.objects.filter(pk=self.instance.marca_id)
        self.fields["categoria"].queryset = categorias.order_by("nombre")
        self.fields["marca"].queryset = marcas.order_by("nombre")
        self.fields["categoria"].label_from_instance = self._label_categoria
        self.fields["marca"].label_from_instance = self._label_marca
        if self.instance and self.instance.pk:
            precio_actual = ProductoPrecio.objects.filter(
                producto=self.instance, activo=True, fecha_fin__isnull=True
            ).order_by("-fecha_inicio").first()
            if precio_actual:
                self.fields["precio"].initial = precio_actual.precio

    @staticmethod
    def _label_categoria(categoria):
        return f"{categoria.nombre} (inactiva)" if not categoria.activo else categoria.nombre

    @staticmethod
    def _label_marca(marca):
        return f"{marca.nombre} (inactiva)" if not marca.activo else marca.nombre

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip()
        existentes = Producto.objects.filter(sku__iexact=sku)
        if self.instance and self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Ya existe un producto con ese SKU.")
        if not sku:
            raise forms.ValidationError("El SKU es obligatorio.")
        return sku

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if not nombre:
            raise forms.ValidationError("El nombre del producto es obligatorio.")
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get("descripcion")
        return descripcion.strip() if descripcion else descripcion


class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ["nombre", "descripcion"]
        labels = {
            "nombre": "Nombre de la categoría",
            "descripcion": "Descripción",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "maxlength": "100", "required": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": "255"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        existentes = CategoriaProducto.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Ya existe una categoría con ese nombre.")
        if not nombre:
            raise forms.ValidationError("El nombre de la categoría es obligatorio.")
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get("descripcion")
        return descripcion.strip() if descripcion else descripcion


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "descripcion"]
        labels = {
            "nombre": "Nombre de la marca",
            "descripcion": "Descripción",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "maxlength": "100", "required": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": "255"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        existentes = Marca.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Ya existe una marca con ese nombre.")
        if not nombre:
            raise forms.ValidationError("El nombre de la marca es obligatorio.")
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get("descripcion")
        return descripcion.strip() if descripcion else descripcion


class BaseStockForm(forms.Form):
    inventario = forms.ModelChoiceField(
        label="Inventario",
        queryset=Inventario.objects.none(),
        widget=forms.Select(attrs={"class": "form-control", "required": True}),
    )
    producto = forms.ModelChoiceField(
        label="Producto",
        queryset=Producto.objects.none(),
        widget=forms.Select(attrs={"class": "form-control", "required": True}),
    )
    motivo = forms.CharField(
        label="Motivo",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "maxlength": "255", "required": True}),
    )
    observacion = forms.CharField(
        label="Observación",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inventario"].queryset = Inventario.objects.filter(activo=True).order_by("nombre")
        self.fields["producto"].queryset = Producto.objects.filter(activo=True).order_by("nombre")

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if not motivo:
            raise forms.ValidationError("El motivo es obligatorio.")
        return motivo

    def clean_observacion(self):
        observacion = self.cleaned_data.get("observacion", "").strip()
        return observacion


class MovimientoStockForm(BaseStockForm):
    tipo_movimiento = forms.ModelChoiceField(
        label="Tipo de movimiento",
        queryset=TipoMovimiento.objects.none(),
        widget=forms.Select(attrs={"class": "form-control", "required": True}),
    )
    cantidad = forms.IntegerField(
        label="Cantidad de unidades",
        min_value=1,
        max_value=MAX_STOCK,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1", "step": "1", "required": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_movimiento"].queryset = TipoMovimiento.objects.filter(
            nombre__in=["Entrada", "Salida"],
            afecta_stock=True,
        ).order_by("nombre")


class AjusteStockForm(BaseStockForm):
    cantidad = forms.IntegerField(
        label="Conteo físico final",
        min_value=0,
        max_value=MAX_STOCK,
        help_text="Ingresa la cantidad real contada; el sistema calculará la diferencia.",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1", "required": True}),
    )


class ExistenciasFiltroForm(forms.Form):
    buscar = forms.CharField(
        required=False,
        label="Buscar producto",
        widget=forms.SearchInput(attrs={
            "class": "form-control",
            "placeholder": "Nombre o código SKU",
        }),
    )
    inventario = forms.ModelChoiceField(
        required=False,
        label="Inventario",
        queryset=Inventario.objects.filter(activo=True).order_by("nombre"),
        empty_label="Todos los inventarios",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    estado = forms.ChoiceField(
        required=False,
        label="Estado del stock",
        choices=(
            ("", "Todos los estados"),
            ("disponible", "Disponible"),
            ("bajo", f"Stock bajo (1 a {LOW_STOCK_THRESHOLD})"),
            ("agotado", "Agotado"),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_buscar(self):
        return self.cleaned_data["buscar"].strip()


class HistorialFiltroForm(forms.Form):
    producto = forms.ModelChoiceField(
        required=False,
        label="Producto",
        queryset=Producto.objects.order_by("nombre"),
        empty_label="Todos los productos",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    tipo = forms.ChoiceField(
        required=False,
        label="Tipo de movimiento",
        choices=(
            ("", "Todos los movimientos"),
            ("Entrada", "Entrada"),
            ("Salida", "Salida"),
            ("Ajuste", "Ajuste"),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    desde = forms.DateField(
        required=False,
        label="Desde",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    hasta = forms.DateField(
        required=False,
        label="Hasta",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        desde = cleaned_data.get("desde")
        hasta = cleaned_data.get("hasta")
        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha «Desde» no puede ser posterior a «Hasta».")
        return cleaned_data
 
