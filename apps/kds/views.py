from collections import defaultdict

from django.db.models import DurationField, ExpressionWrapper, F, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import staff_required
from apps.catalog.models import Category
from apps.employees.decorators import position_required
from apps.employees.models import Employee
from apps.orders.models import Order, OrderItem

from .notify import notify_station


def _table_receipts(station):
    """Agrupa los pedidos de esta estacion en un 'recibo' por mesa.

    Una mesa puede mandar varias rondas (Order) antes de pedir la cuenta;
    todas esas rondas comparten `bill=None` hasta ese momento, asi que se
    consideran la misma sesion abierta. Los items ya entregados de una
    ronda anterior se muestran igual (bloqueados) cuando llega una ronda
    nueva a la misma mesa, para que cocina/bar tenga el contexto completo.
    El recibo deja de mostrarse en cuanto ya no le queda ningun item
    pendiente.
    """
    open_orders = (
        Order.objects.filter(items__product__category__station=station)
        .filter(Q(bill__isnull=True) | ~Q(bill__status="PAGADA"))
        .distinct()
        .select_related("table")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.filter(product__category__station=station)
                .select_related("product")
                .order_by("created_at"),
            )
        )
    )

    receipts_by_key = {}
    for order in open_orders:
        key = order.table_id or f"llevar-{order.id}"
        receipt = receipts_by_key.setdefault(
            key, {"table": order.table, "order_id": order.id, "items": []}
        )
        receipt["items"].extend(order.items.all())

    receipts = [
        receipt
        for receipt in receipts_by_key.values()
        if any(item.status != OrderItem.Status.ENTREGADO for item in receipt["items"])
    ]
    for receipt in receipts:
        receipt["items"].sort(key=lambda item: item.created_at)
        receipt["oldest"] = min(item.created_at for item in receipt["items"])
    receipts.sort(key=lambda receipt: receipt["oldest"])
    return receipts


@position_required(Employee.Position.COCINERO)
def kitchen_display(request):
    receipts = _table_receipts(Category.Station.COCINA)
    return render(
        request,
        "kds/display.html",
        {"receipts": receipts, "title": "Pedido Cocina", "station": "cocina"},
    )


@position_required(Employee.Position.BARTENDER)
def bar_display(request):
    receipts = _table_receipts(Category.Station.BAR)
    return render(
        request,
        "kds/display.html",
        {"receipts": receipts, "title": "Pedido Bar", "station": "bar"},
    )


@position_required(Employee.Position.COCINERO, Employee.Position.BARTENDER)
def start_preparing(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    if request.method == "POST" and item.status == OrderItem.Status.PENDIENTE:
        item.status = OrderItem.Status.EN_PREPARACION
        item.started_at = timezone.now()
        item.started_by = request.user
        item.save(update_fields=["status", "started_at", "started_by"])
        station = "bar" if item.product.category.station == Category.Station.BAR else "cocina"
        notify_station(station)
    if item.product.category.station == Category.Station.BAR:
        return redirect("kds:bar")
    return redirect("kds:kitchen")


@position_required(Employee.Position.COCINERO, Employee.Position.BARTENDER)
def mark_delivered(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    deliverable = (OrderItem.Status.PENDIENTE, OrderItem.Status.EN_PREPARACION)
    if request.method == "POST" and item.status in deliverable:
        item.status = OrderItem.Status.ENTREGADO
        item.delivered_at = timezone.now()
        item.delivered_by = request.user
        item.save(update_fields=["status", "delivered_at", "delivered_by"])
        station = "bar" if item.product.category.station == Category.Station.BAR else "cocina"
        notify_station(station)
    if item.product.category.station == Category.Station.BAR:
        return redirect("kds:bar")
    return redirect("kds:kitchen")


@staff_required
def report_prep_times(request):
    """Tiempo medio por platillo y por quien lo marcó entregado, para detectar
    cuellos de botella en cocina/bar. Cuando el item pasó por "Empezar a
    preparar" (started_at), se desglosa en espera en cola (created_at ->
    started_at) y preparación real (started_at -> delivered_at); si no,
    solo se conoce el total (created_at -> delivered_at)."""
    total_duration = ExpressionWrapper(F("delivered_at") - F("created_at"), output_field=DurationField())
    items = (
        OrderItem.objects.filter(status=OrderItem.Status.ENTREGADO, delivered_at__isnull=False)
        .select_related("product", "delivered_by")
        .annotate(total_time=total_duration)
    )

    by_product = defaultdict(
        lambda: {"seconds": 0.0, "count": 0, "queue_seconds": 0.0, "queue_count": 0, "prep_seconds": 0.0, "prep_count": 0}
    )
    by_staff = defaultdict(lambda: {"seconds": 0.0, "count": 0})
    for item in items:
        seconds = item.total_time.total_seconds()
        bucket = by_product[item.product.name]
        bucket["seconds"] += seconds
        bucket["count"] += 1
        if item.started_at:
            bucket["queue_seconds"] += (item.started_at - item.created_at).total_seconds()
            bucket["queue_count"] += 1
            bucket["prep_seconds"] += (item.delivered_at - item.started_at).total_seconds()
            bucket["prep_count"] += 1
        staff_name = (
            item.delivered_by.get_full_name() or item.delivered_by.username
            if item.delivered_by
            else "Sin registrar"
        )
        by_staff[staff_name]["seconds"] += seconds
        by_staff[staff_name]["count"] += 1

    def _avg(total, count):
        return round(total / count / 60, 1) if count else None

    product_rows = sorted(
        (
            {
                "name": name,
                "avg_minutes": _avg(v["seconds"], v["count"]),
                "avg_queue_minutes": _avg(v["queue_seconds"], v["queue_count"]),
                "avg_prep_minutes": _avg(v["prep_seconds"], v["prep_count"]),
                "count": v["count"],
            }
            for name, v in by_product.items()
        ),
        key=lambda row: -(row["avg_minutes"] or 0),
    )
    staff_rows = sorted(
        (
            {"name": name, "avg_minutes": _avg(v["seconds"], v["count"]), "count": v["count"]}
            for name, v in by_staff.items()
        ),
        key=lambda row: -(row["avg_minutes"] or 0),
    )

    return render(
        request,
        "kds/report_prep_times.html",
        {
            "product_rows": product_rows,
            "staff_rows": staff_rows,
            "chart_product_labels": [row["name"] for row in product_rows],
            "chart_product_minutes": [row["avg_minutes"] for row in product_rows],
            "chart_staff_labels": [row["name"] for row in staff_rows],
            "chart_staff_minutes": [row["avg_minutes"] for row in staff_rows],
        },
    )
