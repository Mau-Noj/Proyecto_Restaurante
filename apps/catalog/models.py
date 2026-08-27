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

    La foto puede subirse como archivo (campo `image`, va a MEDIA_ROOT) o
    quedar como enlace externo (`image_url`, ej. fotos de Wikimedia Commons
    de relleno en los productos de muestra). `display_image_url` decide
    cuál usar: el archivo subido tiene prioridad si existe.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField("Nombre", max_length=150)
    price = models.DecimalField("Precio", max_digits=8, decimal_places=2)
    image = models.ImageField("Foto", upload_to="productos/", blank=True, null=True)
    image_url = models.URLField("Foto (enlace externo)", blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.name

    @property
    def display_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url
