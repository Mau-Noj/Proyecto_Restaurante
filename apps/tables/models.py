from django.db import models


class Table(models.Model):
    """Mesa del salón (RF-MESA-001 Básico: control de ocupación manual)."""

    class Status(models.TextChoices):
        LIBRE = "LIBRE", "Libre"
        OCUPADA = "OCUPADA", "Ocupada"
        CUENTA_PEDIDA = "CUENTA_PEDIDA", "Cuenta Pedida"
        RESERVADA = "RESERVADA", "Reservada"
        LIMPIEZA = "LIMPIEZA", "En Limpieza"

    number = models.PositiveSmallIntegerField("Número", unique=True)
    status = models.CharField(
        "Estado", max_length=20, choices=Status.choices, default=Status.LIBRE
    )

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Mesa {self.number}"
