from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.inventory.services import discount_recipe_for_order
from apps.orders.models import Order, OrderItem

from .models import Table


def _table_cart(request, number: int) -> dict:
    """Carrito por mesa, guardado en la sesion del navegador: {product_id: cantidad}.

    Todavia no hay modelo de Orden en la base de datos - esto permite armar
    el pedido antes de construirlo, sin duplicar ordenes por mesa.
    """
    cart = request.session.setdefault("cart", {})
    return cart.setdefault(str(number), {})


@login_required(login_url="accounts:login_empleado")
def table_select(request):
    tables = Table.objects.order_by("number")
    return render(request, "tables/select.html", {"tables": tables})


@login_required(login_url="accounts:login_empleado")
def table_detail(request, number):
    table = get_object_or_404(Table, number=number)
    categories = Category.objects.order_by("order", "name")
    cart_count = sum(_table_cart(request, number).values())
    return render(
        request,
        "tables/detail.html",
        {"table": table, "categories": categories, "cart_count": cart_count},
    )


@login_required(login_url="accounts:login_empleado")
def category_products(request, number, category_id):
    table = get_object_or_404(Table, number=number)
    category = get_object_or_404(Category, pk=category_id)
    categories = Category.objects.order_by("order", "name")
    table_cart = _table_cart(request, number)
    products = [
        {"product": product, "quantity": table_cart.get(str(product.pk), 0)}
        for product in category.products.all()
    ]
    return render(
        request,
        "tables/category_products.html",
        {"table": table, "category": category, "categories": categories, "products": products},
    )


@login_required(login_url="accounts:login_empleado")
def cart_increment(request, number, category_id, product_id):
    if request.method == "POST":
        get_object_or_404(Table, number=number)
        product = get_object_or_404(Product, pk=product_id)
        table_cart = _table_cart(request, number)
        table_cart[str(product.pk)] = table_cart.get(str(product.pk), 0) + 1
        request.session.modified = True
    return redirect(reverse("tables:category_products", args=[number, category_id]))


@login_required(login_url="accounts:login_empleado")
def cart_decrement(request, number, category_id, product_id):
    if request.method == "POST":
        get_object_or_404(Table, number=number)
        product = get_object_or_404(Product, pk=product_id)
        table_cart = _table_cart(request, number)
        key = str(product.pk)
        if table_cart.get(key, 0) > 0:
            table_cart[key] -= 1
        if table_cart.get(key, 0) <= 0:
            table_cart.pop(key, None)
        request.session.modified = True
    return redirect(reverse("tables:category_products", args=[number, category_id]))


@login_required(login_url="accounts:login_empleado")
def preorder(request, number):
    table = get_object_or_404(Table, number=number)
    categories = Category.objects.order_by("order", "name")
    table_cart = _table_cart(request, number)
    products = Product.objects.filter(pk__in=[int(pid) for pid in table_cart]).select_related(
        "category"
    )

    lines = []
    total = Decimal("0")
    for product in products:
        quantity = table_cart.get(str(product.pk), 0)
        if quantity <= 0:
            continue
        subtotal = product.price * quantity
        total += subtotal
        lines.append({"product": product, "quantity": quantity, "subtotal": subtotal})

    return render(
        request,
        "tables/preorder.html",
        {"table": table, "categories": categories, "lines": lines, "total": total},
    )


@login_required(login_url="accounts:login_empleado")
def submit_order(request, number):
    table = get_object_or_404(Table, number=number)
    table_cart = _table_cart(request, number)

    if request.method == "POST" and table_cart:
        order = Order.objects.create(table=table, created_by=request.user)
        for product_id, quantity in table_cart.items():
            if quantity > 0:
                OrderItem.objects.create(
                    order=order, product_id=int(product_id), quantity=quantity
                )
        discount_recipe_for_order(order, request.user)
        request.session["cart"][str(number)] = {}
        request.session.modified = True
        messages.success(request, "Pedido enviado a cocina/bar.")
        return redirect(reverse("tables:detail", args=[number]))

    return redirect(reverse("tables:preorder", args=[number]))
