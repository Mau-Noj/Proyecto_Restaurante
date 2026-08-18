from django.conf import settings
from django.db import models


class Order(models.Model):
    """Pedido enviado a cocina/bar (RF-ORD-001 Básico)."""

    table = models.ForeignKey("tables.Table", on_delete=models.PROTECT, related_name="orders")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Orden Mesa {self.table.number} · {self.created_at:%H:%M}"


class OrderItem(models.Model):
    """Línea de pedido, enrutada a cocina o bar según la categoría del producto."""

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENTREGADO = "ENTREGADO", "Entregado"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDIENTE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
