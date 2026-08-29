from django import forms

from apps.employees.models import Employee

from .models import Shift

_INPUT_ATTRS = {"class": "field-input"}


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


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["employee", "date", "start_time", "end_time"]
        labels = {
            "employee": "Empleado",
            "date": "Fecha",
            "start_time": "Hora de entrada",
            "end_time": "Hora de salida",
        }
        widgets = {
            "employee": forms.Select(attrs=_INPUT_ATTRS),
            "date": forms.DateInput(attrs={**_INPUT_ATTRS, "type": "date"}),
            "start_time": forms.TimeInput(attrs={**_INPUT_ATTRS, "type": "time"}),
            "end_time": forms.TimeInput(attrs={**_INPUT_ATTRS, "type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.select_related("user").order_by(
            "user__first_name", "user__username"
        )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "Tiene que ser después de la hora de entrada.")
        return cleaned_data


class OvertimeRequestForm(forms.Form):
    minutes = forms.IntegerField(
        label="Minutos extra",
        min_value=5,
        max_value=480,
        widget=forms.NumberInput(attrs=_INPUT_ATTRS),
    )
    note = forms.CharField(
        label="Motivo",
        required=False,
        widget=forms.Textarea(attrs={**_INPUT_ATTRS, "rows": 2}),
    )


class OvertimeResponseForm(forms.Form):
    accepted_minutes = forms.IntegerField(
        label="Minutos que podés hacer",
        min_value=0,
        widget=forms.NumberInput(attrs=_INPUT_ATTRS),
    )
