from django.db import models


class Category(models.Model):
    """Categoría del menú (RF-CAT-001 Básico)."""

    class Station(models.TextChoices):
        COCINA = "COCINA", "Cocina"
        BAR = "BAR", "Bar"

    name = models.CharField("Nombre", max_length=100)
    order = models.PositiveSmallIntegerField("Orden", default=0)
    station = models.CharField(
        "Estación",
        max_length=20,
        choices=Station.choices,
        default=Station.COCINA,
        help_text="A qué pantalla de KDS se enrutan los productos de esta categoría.",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Producto del menú (RF-CAT-001 Básico).

    image_url apunta a una imagen externa (por ahora, fotos de Wikimedia
    Commons como relleno) en vez de un archivo subido — evita depender de
    almacenamiento de medios (S3/MEDIA_ROOT) hasta que se defina esa pieza.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField("Nombre", max_length=150)
    price = models.DecimalField("Precio", max_digits=8, decimal_places=2)
    image_url = models.URLField("Imagen", blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.name
