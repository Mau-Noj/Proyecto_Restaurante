from django import forms

from .models import Kiosk

_INPUT_ATTRS = {"class": "field-input"}

# Ubicaciones típicas de un bistro -- se elige de la lista para no tener
# que escribir el nombre cada vez; "Otro" deja un campo libre para el
# caso que no esté contemplado.
KIOSK_LOCATION_CHOICES = [
    ("Caja", "Caja"),
    ("Cocina", "Cocina"),
    ("Bar", "Bar"),
    ("Entrada del Personal", "Entrada del Personal"),
    ("otro", "Otro..."),
]


class KioskForm(forms.ModelForm):
    name = forms.ChoiceField(
        label="Ubicación",
        choices=KIOSK_LOCATION_CHOICES,
        widget=forms.Select(attrs={**_INPUT_ATTRS, "id": "id_location"}),
    )
    custom_name = forms.CharField(
        label="Especificar ubicación",
        required=False,
        widget=forms.TextInput(
            attrs={**_INPUT_ATTRS, "placeholder": "Ej. Segundo piso", "id": "id_custom_name"}
        ),
    )

    class Meta:
        model = Kiosk
        fields = ["name"]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("name") == "otro":
            custom_name = cleaned_data.get("custom_name", "").strip()
            if not custom_name:
                # No se sobreescribe cleaned_data["name"] a vacío: eso
                # dispararía además la validación de "blank" del modelo
                # sobre un campo que el usuario ni ve como tal (es el
                # select), duplicando el mensaje de error.
                self.add_error("custom_name", "Especificá el nombre de la ubicación.")
            else:
                cleaned_data["name"] = custom_name
        return cleaned_data


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
