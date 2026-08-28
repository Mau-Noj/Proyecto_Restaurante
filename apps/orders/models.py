from django.conf import settings
from django.db import models


class Order(models.Model):
    """Pedido enviado a cocina/bar (RF-ORD-001 Básico).

    `table` queda vacío para pedidos para llevar (RF-PAG-001 Básico), que se
    cobran de inmediato en caja en vez de quedar asociados a una mesa.
    """

    table = models.ForeignKey(
        "tables.Table", null=True, blank=True, on_delete=models.PROTECT, related_name="orders"
    )
    bill = models.ForeignKey(
        "payments.Bill", null=True, blank=True, on_delete=models.PROTECT, related_name="orders"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = f"Mesa {self.table.number}" if self.table_id else "Para Llevar"
        return f"Orden {target} · {self.created_at:%H:%M}"


class OrderItem(models.Model):
    """Línea de pedido, enrutada a cocina o bar según la categoría del producto."""

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENTREGADO = "ENTREGADO", "Entregado"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    notes = models.CharField(
        "Notas", max_length=200, blank=True, default="", help_text='Ej. "sin cebolla", "bien cocido"'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDIENTE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="items_delivered",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
