from django.conf import settings
from django.db import models


class Employee(models.Model):
    """Ficha de personal (RF-REG-001-BASICO). Datos de acceso viven en el User."""

    class Position(models.TextChoices):
        GERENTE = "GERENTE", "Administrador / Gerente"
        MESERO = "MESERO", "Mesero"
        COCINERO = "COCINERO", "Cocinero"
        BARTENDER = "BARTENDER", "Bartender"
        CAJERO = "CAJERO", "Cajero"
        HOSTESS = "HOSTESS", "Hostess"
        BODEGUERO = "BODEGUERO", "Bodeguero"
        COMPRAS = "COMPRAS", "Encargado de Compras"
        REPARTIDOR = "REPARTIDOR", "Repartidor"
        KIOSKO = "KIOSKO", "Kiosko (pantalla de asistencia)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profile"
    )
    phone = models.CharField("Teléfono", max_length=20, blank=True)
    position = models.CharField("Puesto", max_length=20, choices=Position.choices)
    hire_date = models.DateField("Fecha de contratación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.get_full_name() or self.user.username
