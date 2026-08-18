import secrets
import string
import unicodedata

from django import forms
from django.contrib.auth import get_user_model

from .models import Employee

User = get_user_model()

_INPUT_ATTRS = {"class": "field-input"}


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


def reset_employee_password(employee: Employee) -> str:
    """Genera una nueva contraseña temporal y exige cambiarla en el próximo login."""
    temp_password = generate_temp_password()
    user = employee.user
    user.set_password(temp_password)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    return temp_password


class EmployeeCreateForm(forms.Form):
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


class EmployeeEditForm(forms.Form):
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
    is_active = forms.BooleanField(
        label="Cuenta activa",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded accent-neon-cyan"}),
    )

    def __init__(self, *args, employee: Employee, **kwargs):
        self.employee = employee
        kwargs.setdefault(
            "initial",
            {
                "first_name": employee.user.first_name,
                "last_name": employee.user.last_name,
                "email": employee.user.email,
                "phone": employee.phone,
                "position": employee.position,
                "hire_date": employee.hire_date,
                "is_active": employee.user.is_active,
            },
        )
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.employee.user_id).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con ese correo.")
        return email

    def save(self) -> Employee:
        data = self.cleaned_data
        user = self.employee.user
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        user.email = data["email"]
        user.is_active = data["is_active"]
        user.save(update_fields=["first_name", "last_name", "email", "is_active"])

        self.employee.phone = data["phone"]
        self.employee.position = data["position"]
        self.employee.hire_date = data["hire_date"]
        self.employee.save(update_fields=["phone", "position", "hire_date", "updated_at"])
        return self.employee


class ConfirmPasswordForm(forms.Form):
    """Reconfirmación de la contraseña del admin logueado, para acciones destructivas."""

    password = forms.CharField(
        label="Tu contraseña",
        widget=forms.PasswordInput(attrs=_INPUT_ATTRS),
    )

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Contraseña incorrecta.")
        return password
