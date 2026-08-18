from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.tables.models import Table

from .models import Bill, PaymentSplit


def _orders_subtotal(orders) -> Decimal:
    total = Decimal("0")
    for order in orders:
        for item in order.items.select_related("product"):
            total += item.product.price * item.quantity
    return total


def bill_lines(bill: Bill) -> list[dict]:
    """Ítems de la cuenta agrupados por producto, sumando todas las rondas."""
    lines: dict[int, dict] = {}
    for order in bill.orders.prefetch_related("items__product"):
        for item in order.items.all():
            entry = lines.setdefault(
                item.product_id,
                {"product": item.product, "quantity": 0, "subtotal": Decimal("0")},
            )
            entry["quantity"] += item.quantity
            entry["subtotal"] += item.product.price * item.quantity
    return list(lines.values())


@transaction.atomic
def open_bill_for_table(table: Table, opened_by) -> Bill:
    """Reabre (o crea) la Cuenta abierta de una mesa, agrupando todas las
    rondas (Órdenes) que todavía no están facturadas."""
    bill = Bill.objects.filter(table=table, status=Bill.Status.ABIERTA).first()
    if bill is None:
        bill = Bill.objects.create(
            table=table, bill_type=Bill.BillType.MESA, opened_by=opened_by
        )
    Order.objects.filter(table=table, bill__isnull=True).update(bill=bill)
    bill.subtotal = _orders_subtotal(bill.orders.all())
    bill.total = bill.subtotal + bill.tip
    bill.save(update_fields=["subtotal", "total"])
    table.status = Table.Status.CUENTA_PEDIDA
    table.save(update_fields=["status"])
    return bill


def open_bill_for_takeout(order: Order, opened_by) -> Bill:
    bill = Bill.objects.create(bill_type=Bill.BillType.LLEVAR, opened_by=opened_by)
    order.bill = bill
    order.save(update_fields=["bill"])
    bill.subtotal = _orders_subtotal([order])
    bill.total = bill.subtotal
    bill.save(update_fields=["subtotal", "total"])
    return bill


def set_tip(bill: Bill, tip: Decimal) -> Bill:
    bill.tip = tip
    bill.total = bill.subtotal + tip
    bill.save(update_fields=["tip", "total"])
    return bill


def add_split(bill: Bill, *, label: str, method: str, amount: Decimal) -> PaymentSplit:
    return PaymentSplit.objects.create(bill=bill, label=label, method=method, amount=amount)


@transaction.atomic
def close_bill(bill: Bill, closed_by) -> Bill:
    bill.status = Bill.Status.PAGADA
    bill.closed_by = closed_by
    bill.closed_at = timezone.now()
    bill.save(update_fields=["status", "closed_by", "closed_at"])
    if bill.table_id:
        bill.table.status = Table.Status.LIMPIEZA
        bill.table.save(update_fields=["status"])
    return bill
