from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import ExtractHour
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.accounts.decorators import staff_required
from apps.catalog.models import Category, Product
from apps.employees.decorators import position_required
from apps.employees.models import Employee
from apps.inventory.services import discount_recipe_for_order
from apps.kds.notify import notify_order_stations
from apps.orders.models import Order, OrderItem
from apps.tables.models import Table

from .forms import DISCOUNT_PRESETS, TIP_PRESETS, DiscountForm, SplitForm, TipForm
from .models import Bill, PaymentSplit
from .services import (
    bill_lines,
    close_bill,
    open_bill_for_table,
    open_bill_for_takeout,
    set_discount,
    set_tip,
)

# --- Mesa: abrir/cancelar el cobro de una mesa (mesero) ---------------------


@login_required(login_url="accounts:login_empleado")
def open_table_bill(request, number):
    table = get_object_or_404(Table, number=number)
    if request.method == "POST":
        bill = open_bill_for_table(table, request.user)
        return redirect(reverse("payments:bill_detail", args=[bill.pk]))
    return redirect(reverse("tables:detail", args=[number]))


@login_required(login_url="accounts:login_empleado")
def cancel_table_bill(request, number):
    table = get_object_or_404(Table, number=number)
    if request.method == "POST" and table.status == Table.Status.CUENTA_PEDIDA:
        table.status = Table.Status.OCUPADA
        table.save(update_fields=["status"])
    return redirect(reverse("tables:detail", args=[number]))


# --- Pantalla de Reportar Pago (compartida: mesa y para llevar) ------------


@login_required(login_url="accounts:login_empleado")
def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    tip_form = TipForm(subtotal=bill.subtotal)
    discount_base = bill.subtotal + bill.tip
    discount_form = DiscountForm(base_total=discount_base)
    split_form = SplitForm(initial={"label": f"Persona {bill.splits.count() + 1}"})
    tip_suggestions = [
        (pct, (bill.subtotal * Decimal(pct) / Decimal("100")).quantize(Decimal("0.01")))
        for pct in TIP_PRESETS
    ]
    discount_suggestions = [
        (pct, (discount_base * Decimal(pct) / Decimal("100")).quantize(Decimal("0.01")))
        for pct in DISCOUNT_PRESETS
    ]
    return render(
        request,
        "payments/bill_detail.html",
        {
            "bill": bill,
            "lines": bill_lines(bill),
            "tip_form": tip_form,
            "split_form": split_form,
            "tip_suggestions": tip_suggestions,
            "discount_form": discount_form,
            "discount_suggestions": discount_suggestions,
        },
    )


@login_required(login_url="accounts:login_empleado")
def set_bill_tip(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == "POST":
        form = TipForm(request.POST, subtotal=bill.subtotal)
        if form.is_valid():
            set_tip(bill, form.cleaned_data["tip"])
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    return redirect(reverse("payments:bill_detail", args=[bill.pk]))


@login_required(login_url="accounts:login_empleado")
def set_bill_discount(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == "POST":
        form = DiscountForm(request.POST, base_total=bill.subtotal + bill.tip)
        if form.is_valid():
            set_discount(bill, form.cleaned_data["discount"])
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    return redirect(reverse("payments:bill_detail", args=[bill.pk]))


@login_required(login_url="accounts:login_empleado")
def add_bill_split(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == "POST":
        form = SplitForm(request.POST)
        if form.is_valid():
            PaymentSplit.objects.create(
                bill=bill,
                label=form.cleaned_data["label"],
                method=form.cleaned_data["method"],
                amount=form.cleaned_data["amount"],
            )
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    return redirect(reverse("payments:bill_detail", args=[bill.pk]))


@login_required(login_url="accounts:login_empleado")
def remove_bill_split(request, pk, split_id):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == "POST":
        PaymentSplit.objects.filter(pk=split_id, bill=bill).delete()
    return redirect(reverse("payments:bill_detail", args=[bill.pk]))


@login_required(login_url="accounts:login_empleado")
def confirm_bill(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == "POST":
        if bill.balance_due > 0:
            messages.error(request, "Todavía falta cubrir el total de la cuenta.")
            return redirect(reverse("payments:bill_detail", args=[bill.pk]))
        close_bill(bill, request.user)
        messages.success(request, "Pago confirmado.")
        if bill.bill_type == Bill.BillType.MESA:
            return redirect(reverse("tables:select"))
        return redirect(reverse("payments:takeout_new"))
    return redirect(reverse("payments:bill_detail", args=[bill.pk]))


# --- Caja: pedidos para llevar (Cajero) -------------------------------------


def _takeout_cart(request) -> dict:
    return request.session.setdefault("takeout_cart", {})


@position_required(Employee.Position.CAJERO)
def takeout_new(request):
    categories = Category.objects.order_by("order", "name")
    cart_count = sum(_takeout_cart(request).values())
    return render(
        request, "payments/takeout_new.html", {"categories": categories, "cart_count": cart_count}
    )


@position_required(Employee.Position.CAJERO)
def takeout_category_products(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    categories = Category.objects.order_by("order", "name")
    takeout_cart = _takeout_cart(request)
    products = [
        {"product": product, "quantity": takeout_cart.get(str(product.pk), 0)}
        for product in category.products.all()
    ]
    return render(
        request,
        "payments/takeout_category_products.html",
        {"category": category, "categories": categories, "products": products},
    )


@position_required(Employee.Position.CAJERO)
def takeout_cart_increment(request, category_id, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=product_id)
        takeout_cart = _takeout_cart(request)
        takeout_cart[str(product.pk)] = takeout_cart.get(str(product.pk), 0) + 1
        request.session.modified = True
    return redirect(reverse("payments:takeout_category_products", args=[category_id]))


@position_required(Employee.Position.CAJERO)
def takeout_cart_decrement(request, category_id, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=product_id)
        takeout_cart = _takeout_cart(request)
        key = str(product.pk)
        if takeout_cart.get(key, 0) > 0:
            takeout_cart[key] -= 1
        if takeout_cart.get(key, 0) <= 0:
            takeout_cart.pop(key, None)
        request.session.modified = True
    return redirect(reverse("payments:takeout_category_products", args=[category_id]))


@position_required(Employee.Position.CAJERO)
def takeout_cart_view(request):
    takeout_cart = _takeout_cart(request)
    products = Product.objects.filter(pk__in=[int(pid) for pid in takeout_cart]).select_related(
        "category"
    )
    lines = []
    total = Decimal("0")
    for product in products:
        quantity = takeout_cart.get(str(product.pk), 0)
        if quantity <= 0:
            continue
        subtotal = product.price * quantity
        total += subtotal
        lines.append({"product": product, "quantity": quantity, "subtotal": subtotal})
    return render(request, "payments/takeout_cart.html", {"lines": lines, "total": total})


@position_required(Employee.Position.CAJERO)
def takeout_checkout(request):
    takeout_cart = _takeout_cart(request)
    if request.method == "POST" and takeout_cart:
        order = Order.objects.create(table=None, created_by=request.user)
        for product_id, quantity in takeout_cart.items():
            if quantity > 0:
                OrderItem.objects.create(
                    order=order, product_id=int(product_id), quantity=quantity
                )
        discount_recipe_for_order(order, request.user)
        notify_order_stations(order)
        bill = open_bill_for_takeout(order, request.user)
        request.session["takeout_cart"] = {}
        request.session.modified = True
        return redirect(reverse("payments:bill_detail", args=[bill.pk]))
    return redirect(reverse("payments:takeout_cart"))


# --- Reportes (admin) --------------------------------------------------------


@staff_required
def index(request):
    return render(request, "payments/index.html")


@staff_required
def report_by_waiter(request):
    bills = Bill.objects.filter(status=Bill.Status.PAGADA).select_related("closed_by")
    rows = {}
    for bill in bills:
        user = bill.closed_by
        row = rows.setdefault(
            user.pk,
            {"user": user, "count": 0, "total_sales": Decimal("0"), "total_tips": Decimal("0")},
        )
        row["count"] += 1
        row["total_sales"] += bill.subtotal
        row["total_tips"] += bill.tip
    return render(request, "payments/report_by_waiter.html", {"rows": rows.values()})


@staff_required
def report_shift(request):
    date_param = request.GET.get("fecha")
    target_date = parse_date(date_param) if date_param else timezone.localdate()
    if target_date is None:
        target_date = timezone.localdate()

    bills = (
        Bill.objects.filter(status=Bill.Status.PAGADA, closed_at__date=target_date)
        .select_related("table", "closed_by")
        .prefetch_related("splits")
    )
    totals_by_method = defaultdict(Decimal)
    grand_total = Decimal("0")
    tip_total = Decimal("0")
    for bill in bills:
        grand_total += bill.total
        tip_total += bill.tip
        for split in bill.splits.all():
            totals_by_method[split.method] += split.amount

    method_rows = [
        {"method": method, "label": label, "total": totals_by_method.get(method, Decimal("0"))}
        for method, label in PaymentSplit.Method.choices
    ]
    return render(
        request,
        "payments/report_shift.html",
        {
            "target_date": target_date,
            "bills": bills,
            "method_rows": method_rows,
            "grand_total": grand_total,
            "tip_total": tip_total,
            "chart_labels": [row["label"] for row in method_rows],
            "chart_totals": [float(row["total"]) for row in method_rows],
        },
    )


@staff_required
def report_audit(request):
    bills = Bill.objects.filter(status=Bill.Status.PAGADA).select_related("table", "closed_by")
    waiter_totals = defaultdict(lambda: {"sales": Decimal("0"), "tips": Decimal("0")})
    for bill in bills:
        name = bill.closed_by.get_full_name() or bill.closed_by.username
        waiter_totals[name]["sales"] += bill.total
        waiter_totals[name]["tips"] += bill.tip

    chart_labels = list(waiter_totals.keys())
    sales_data = [float(v["sales"]) for v in waiter_totals.values()]
    tips_data = [float(v["tips"]) for v in waiter_totals.values()]

    return render(
        request,
        "payments/report_audit.html",
        {
            "bills": bills,
            "chart_labels": chart_labels,
            "sales_data": sales_data,
            "tips_data": tips_data,
        },
    )


@staff_required
def report_top_products(request):
    """Platos más vendidos y horas pico (RF-BI), en un rango de fechas (30 días por defecto)."""
    hasta = parse_date(request.GET.get("hasta", "")) or timezone.localdate()
    desde = parse_date(request.GET.get("desde", "")) or hasta - timedelta(days=30)

    items = OrderItem.objects.filter(
        order__created_at__date__gte=desde, order__created_at__date__lte=hasta
    )
    revenue_expr = ExpressionWrapper(
        F("quantity") * F("product__price"), output_field=DecimalField(max_digits=12, decimal_places=2)
    )
    product_rows = list(
        items.values("product__name")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum(revenue_expr))
        .order_by("-total_quantity")[:15]
    )

    hour_counts = {
        row["hour"]: row["count"]
        for row in Order.objects.filter(created_at__date__gte=desde, created_at__date__lte=hasta)
        .annotate(hour=ExtractHour("created_at", tzinfo=timezone.get_current_timezone()))
        .values("hour")
        .annotate(count=Count("id"))
    }
    hour_labels = [f"{hour:02d}:00" for hour in range(24)]
    hour_data = [hour_counts.get(hour, 0) for hour in range(24)]

    return render(
        request,
        "payments/report_top_products.html",
        {
            "desde": desde,
            "hasta": hasta,
            "product_rows": product_rows,
            "chart_product_labels": [row["product__name"] for row in product_rows],
            "chart_product_quantities": [row["total_quantity"] for row in product_rows],
            "chart_hour_labels": hour_labels,
            "chart_hour_data": hour_data,
        },
    )
