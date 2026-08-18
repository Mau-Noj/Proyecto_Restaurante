from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.catalog.models import Category
from apps.employees.decorators import position_required
from apps.employees.models import Employee
from apps.orders.models import OrderItem


def _pending_items(station):
    return (
        OrderItem.objects.filter(
            status=OrderItem.Status.PENDIENTE, product__category__station=station
        )
        .select_related("product", "order__table")
        .order_by("created_at")
    )


@position_required(Employee.Position.COCINERO)
def kitchen_display(request):
    items = _pending_items(Category.Station.COCINA)
    return render(request, "kds/display.html", {"items": items, "title": "Pedido Cocina"})


@position_required(Employee.Position.BARTENDER)
def bar_display(request):
    items = _pending_items(Category.Station.BAR)
    return render(request, "kds/display.html", {"items": items, "title": "Pedido Bar"})


@position_required(Employee.Position.COCINERO, Employee.Position.BARTENDER)
def mark_delivered(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    if request.method == "POST":
        item.status = OrderItem.Status.ENTREGADO
        item.delivered_at = timezone.now()
        item.save(update_fields=["status", "delivered_at"])
    if item.product.category.station == Category.Station.BAR:
        return redirect("kds:bar")
    return redirect("kds:kitchen")
