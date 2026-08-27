from django import forms

from .models import Category, Product

_INPUT_ATTRS = {"class": "field-input"}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "order", "station"]
        labels = {
            "name": "Nombre",
            "order": "Orden",
            "station": "Estación (KDS)",
        }
        widgets = {
            "name": forms.TextInput(attrs=_INPUT_ATTRS),
            "order": forms.NumberInput(attrs={**_INPUT_ATTRS, "min": "0"}),
            "station": forms.Select(attrs=_INPUT_ATTRS),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "price", "image", "image_url", "order"]
        labels = {
            "category": "Categoría",
            "name": "Nombre",
            "price": "Precio (Q)",
            "image": "Subir foto",
            "image_url": "O enlace externo",
            "order": "Orden",
        }
        widgets = {
            "category": forms.Select(attrs=_INPUT_ATTRS),
            "name": forms.TextInput(attrs=_INPUT_ATTRS),
            "price": forms.NumberInput(attrs={**_INPUT_ATTRS, "step": "0.01", "min": "0"}),
            "image": forms.ClearableFileInput(attrs={**_INPUT_ATTRS, "accept": "image/*"}),
            "image_url": forms.URLInput(
                attrs={**_INPUT_ATTRS, "placeholder": "https://..."}
            ),
            "order": forms.NumberInput(attrs={**_INPUT_ATTRS, "min": "0"}),
        }
