from django import forms
from .models import CategoriaProducto, Marca, Producto, ProductoPrecio


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
        self.fields["categoria"].queryset = CategoriaProducto.objects.filter(activo=True).order_by("nombre")
        self.fields["marca"].queryset = Marca.objects.filter(activo=True).order_by("nombre")
        if self.instance and self.instance.pk:
            precio_actual = ProductoPrecio.objects.filter(
                producto=self.instance, activo=True, fecha_fin__isnull=True
            ).order_by("-fecha_inicio").first()
            if precio_actual:
                self.fields["precio"].initial = precio_actual.precio

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
