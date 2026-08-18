from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from apps.catalog.models import Product

from .models import Ingredient, RecipeItem, StockMovement

_INPUT_ATTRS = {"class": "field-input"}
_QTY_ATTRS = {**_INPUT_ATTRS, "step": "0.01", "min": "0.01"}


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ["name", "unit", "stock", "min_stock", "unit_cost"]
        labels = {
            "name": "Nombre",
            "unit": "Unidad de medida",
            "stock": "Stock actual",
            "min_stock": "Stock mínimo",
            "unit_cost": "Costo unitario",
        }
        widgets = {
            "name": forms.TextInput(attrs=_INPUT_ATTRS),
            "unit": forms.Select(attrs=_INPUT_ATTRS),
            "stock": forms.NumberInput(attrs={**_INPUT_ATTRS, "step": "0.01", "min": "0"}),
            "min_stock": forms.NumberInput(attrs={**_INPUT_ATTRS, "step": "0.01", "min": "0"}),
            "unit_cost": forms.NumberInput(attrs={**_INPUT_ATTRS, "step": "0.01", "min": "0"}),
        }


class StockEntryForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        label="Ingrediente",
        queryset=Ingredient.objects.all(),
        widget=forms.Select(attrs=_INPUT_ATTRS),
    )
    quantity = forms.DecimalField(
        label="Cantidad",
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs=_QTY_ATTRS),
    )
    reference = forms.CharField(
        label="Proveedor / Factura",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={**_INPUT_ATTRS, "placeholder": "Ej. Distribuidora XYZ - Factura 4521"}
        ),
    )


class StockExitForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        label="Ingrediente",
        queryset=Ingredient.objects.all(),
        widget=forms.Select(attrs=_INPUT_ATTRS),
    )
    movement_type = forms.ChoiceField(
        label="Motivo",
        choices=[
            (StockMovement.MovementType.MERMA, "Merma"),
            (StockMovement.MovementType.CADUCIDAD, "Caducidad"),
        ],
        widget=forms.Select(attrs=_INPUT_ATTRS),
    )
    quantity = forms.DecimalField(
        label="Cantidad",
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs=_QTY_ATTRS),
    )
    reference = forms.CharField(
        label="Detalle",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={**_INPUT_ATTRS, "placeholder": "Ej. Se cayó la bandeja"}),
    )


RecipeItemFormSet = inlineformset_factory(
    Product,
    RecipeItem,
    fields=["ingredient", "quantity"],
    extra=3,
    can_delete=True,
    widgets={
        "ingredient": forms.Select(attrs=_INPUT_ATTRS),
        "quantity": forms.NumberInput(attrs=_QTY_ATTRS),
    },
)
