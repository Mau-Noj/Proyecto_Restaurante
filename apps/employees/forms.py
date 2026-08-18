import secrets
import string
import unicodedata

from django import forms
from django.contrib.auth import get_user_model

from .models import Employee

User = get_user_model()


def _slugify_username(first_name: str, last_name: str) -> str:
    raw = f"{first_name}.{last_name}".lower().strip()
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch for ch in normalized if ch.isalnum() or ch == ".")
    return cleaned or "empleado"


def generate_unique_username(first_name: str, last_name: str) -> str:
    base = _slugify_username(first_name, last_name)
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


class EmployeeCreateForm(forms.Form):
    _INPUT_ATTRS = {"class": "field-input"}

    first_name = forms.CharField(
        label="Nombre", max_length=150, widget=forms.TextInput(attrs=_INPUT_ATTRS)
    )
    last_name = forms.CharField(
        label="Apellido", max_length=150, widget=forms.TextInput(attrs=_INPUT_ATTRS)
    )
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs=_INPUT_ATTRS))
    phone = forms.CharField(
        label="Teléfono", max_length=20, required=False, widget=forms.TextInput(attrs=_INPUT_ATTRS)
    )
    position = forms.ChoiceField(
        label="Puesto", choices=Employee.Position.choices, widget=forms.Select(attrs=_INPUT_ATTRS)
    )
    hire_date = forms.DateField(
        label="Fecha de contratación",
        widget=forms.DateInput(attrs={**_INPUT_ATTRS, "type": "date"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con ese correo.")
        return email

    def save(self) -> tuple[Employee, str]:
        """Crea el User (credenciales generadas) y el Employee. Devuelve (employee, password)."""
        data = self.cleaned_data
        username = generate_unique_username(data["first_name"], data["last_name"])
        temp_password = generate_temp_password()

        user = User.objects.create_user(
            username=username,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            password=temp_password,
            is_staff=False,
        )
        employee = Employee.objects.create(
            user=user,
            phone=data["phone"],
            position=data["position"],
            hire_date=data["hire_date"],
        )
        return employee, temp_password
