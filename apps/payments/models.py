from decimal import Decimal

from django.conf import settings
from django.db import models


class Bill(models.Model):
    """Cuenta a cobrar (RF-PAG-001 Básico).

    Agrupa una o varias Órdenes (rondas) enviadas para una misma mesa, o la
    Órden única de un pedido para llevar. Se cierra con uno o varios
    PaymentSplit hasta cubrir el total.
    """

    class BillType(models.TextChoices):
        MESA = "MESA", "Mesa"
        LLEVAR = "LLEVAR", "Para Llevar"

    class Status(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        PAGADA = "PAGADA", "Pagada"

    table = models.ForeignKey(
        "tables.Table", null=True, blank=True, on_delete=models.PROTECT, related_name="bills"
    )
    bill_type = models.CharField("Tipo", max_length=10, choices=BillType.choices)
    status = models.CharField(
        "Estado", max_length=10, choices=Status.choices, default=Status.ABIERTA
    )
    subtotal = models.DecimalField("Subtotal", max_digits=10, decimal_places=2, default=0)
    tip = models.DecimalField("Propina", max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField("Total", max_digits=10, decimal_places=2, default=0)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bills_opened"
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="bills_closed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cuenta"
        verbose_name_plural = "Cuentas"

    def __str__(self):
        target = f"Mesa {self.table.number}" if self.table_id else "Para Llevar"
        return f"Cuenta {target} · Q{self.total}"

    @property
    def paid_amount(self) -> Decimal:
        return sum((split.amount for split in self.splits.all()), Decimal("0"))

    @property
    def balance_due(self) -> Decimal:
        return self.total - self.paid_amount


class PaymentSplit(models.Model):
    """Un pago parcial dentro de una Cuenta ("Persona 1", "Persona 2"...)."""

    class Method(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TARJETA = "TARJETA", "Tarjeta"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        PAGO_MOVIL = "PAGO_MOVIL", "Pago Móvil"

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="splits")
    label = models.CharField("Persona", max_length=50, blank=True)
    method = models.CharField("Método", max_length=20, choices=Method.choices)
    amount = models.DecimalField("Monto", max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"{self.label or self.get_method_display()} · Q{self.amount}"
