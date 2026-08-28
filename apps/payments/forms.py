from decimal import Decimal

from django import forms

from .models import PaymentSplit

_INPUT_ATTRS = {"class": "field-input"}

TIP_PRESETS = ["10", "12", "15"]


class CommaDecimalField(forms.DecimalField):
    """DecimalField que acepta coma o punto como separador decimal.

    Un <input type="number"> rechaza "50,00" en silencio (el navegador
    manda el campo vacio) en cualquier configuracion regional que use
    coma para decimales -- el usuario cree que no escribio nada, cuando
    en realidad el valor nunca llego a validarse. Por eso el widget es
    de texto (con teclado numerico en movil via inputmode) en vez de
    number, y aqui se normaliza la coma antes de intentar convertir a
    Decimal.
    """

    widget = forms.TextInput

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return super().to_python(value)


class TipForm(forms.Form):
    preset = forms.ChoiceField(
        label="Propina sugerida",
        choices=[(pct, f"{pct}%") for pct in TIP_PRESETS] + [("custom", "Personalizada")],
        widget=forms.RadioSelect,
    )
    custom_amount = CommaDecimalField(
        label="Monto personalizado",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        widget=forms.TextInput(
            attrs={**_INPUT_ATTRS, "inputmode": "decimal", "placeholder": "0.00"}
        ),
    )

    def __init__(self, *args, subtotal: Decimal, **kwargs):
        self.subtotal = subtotal
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get("preset")
        if preset == "custom":
            if cleaned_data.get("custom_amount") is None:
                self.add_error("custom_amount", "Ingresa el monto de la propina.")
                return cleaned_data
            cleaned_data["tip"] = cleaned_data["custom_amount"]
        elif preset:
            cleaned_data["tip"] = (self.subtotal * Decimal(preset) / Decimal("100")).quantize(
                Decimal("0.01")
            )
        return cleaned_data


class SplitForm(forms.Form):
    label = forms.CharField(
        label="Nombre o NIT",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={**_INPUT_ATTRS, "placeholder": "Ej. Persona 1 o NIT 1234567-8"}
        ),
    )
    method = forms.ChoiceField(
        label="Método", choices=PaymentSplit.Method.choices, widget=forms.Select(attrs=_INPUT_ATTRS)
    )
    amount = CommaDecimalField(
        label="Monto",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.TextInput(
            attrs={**_INPUT_ATTRS, "inputmode": "decimal", "placeholder": "0.00"}
        ),
    )
