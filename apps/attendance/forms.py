from django import forms

from .models import Kiosk

_INPUT_ATTRS = {"class": "field-input"}


class KioskForm(forms.ModelForm):
    class Meta:
        model = Kiosk
        fields = ["name"]
        labels = {"name": "Nombre / Ubicación"}
        widgets = {
            "name": forms.TextInput(
                attrs={**_INPUT_ATTRS, "placeholder": "Ej. Pantalla de Caja"}
            ),
        }


class AdjustmentForm(forms.Form):
    reason = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(
            attrs={
                **_INPUT_ATTRS,
                "rows": 3,
                "placeholder": "Ej. Se le olvidó marcar salida, confirmado con el empleado.",
            }
        ),
    )
    new_timestamp = forms.DateTimeField(
        label="Hora correcta",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={**_INPUT_ATTRS, "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
    )
