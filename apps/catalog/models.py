from django.db import models


class Category(models.Model):
    """Categoría del menú (RF-CAT-001 Básico)."""

    name = models.CharField("Nombre", max_length=100)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name
