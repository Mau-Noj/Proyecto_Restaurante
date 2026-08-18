from django.conf import settings
from django.db import models


class Ingredient(models.Model):
    """Insumo de bodega (RF-INV-001 Básico)."""

    class Unit(models.TextChoices):
        KG = "KG", "Kilogramos"
        G = "G", "Gramos"
        L = "L", "Litros"
        ML = "ML", "Mililitros"
        UNIDAD = "UNIDAD", "Unidades"

    name = models.CharField("Nombre", max_length=150)
    unit = models.CharField("Unidad de medida", max_length=10, choices=Unit.choices)
    stock = models.DecimalField("Stock actual", max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField("Stock mínimo", max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Costo unitario", max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"

    def __str__(self):
        return self.name

    @property
    def status(self) -> str:
        """Semáforo de stock: CRITICO / BAJO / SEGURO."""
        if self.stock <= 0 or self.stock <= self.min_stock / 2:
            return "CRITICO"
        if self.stock <= self.min_stock:
            return "BAJO"
        return "SEGURO"

    @property
    def status_label(self) -> str:
        return {"CRITICO": "Crítico", "BAJO": "Bajo", "SEGURO": "Seguro"}[self.status]


class RecipeItem(models.Model):
    """Receta / BOM: cuánto de cada ingrediente lleva un producto (RF-INV-002 Básico)."""

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="recipe_items"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT, related_name="recipe_items"
    )
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["ingredient__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "ingredient"], name="unique_recipe_product_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.product} - {self.ingredient} ({self.quantity} {self.ingredient.unit})"


class StockMovement(models.Model):
    """Kardex de movimientos de inventario (RF-INV-003 Básico)."""

    class MovementType(models.TextChoices):
        COMPRA = "COMPRA", "Compra"
        MERMA = "MERMA", "Merma"
        CADUCIDAD = "CADUCIDAD", "Caducidad"
        VENTA = "VENTA", "Venta"

    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField("Movimiento", max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=2)
    reference = models.CharField("Referencia", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.ingredient} ({self.quantity})"
