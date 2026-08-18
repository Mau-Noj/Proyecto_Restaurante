from django.db import models


class Table(models.Model):
    """Mesa del salón (RF-MESA-001 Básico: control de ocupación manual)."""

    number = models.PositiveSmallIntegerField("Número", unique=True)
    is_occupied = models.BooleanField("Ocupada", default=False)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Mesa {self.number}"
