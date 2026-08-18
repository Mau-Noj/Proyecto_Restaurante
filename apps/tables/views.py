from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.catalog.models import Category

from .models import Table


@login_required(login_url="accounts:login_empleado")
def table_select(request):
    tables = Table.objects.order_by("number")
    return render(request, "tables/select.html", {"tables": tables})


@login_required(login_url="accounts:login_empleado")
def table_detail(request, number):
    table = get_object_or_404(Table, number=number)
    categories = Category.objects.order_by("order", "name")
    return render(request, "tables/detail.html", {"table": table, "categories": categories})


@login_required(login_url="accounts:login_empleado")
def category_products(request, number, category_id):
    table = get_object_or_404(Table, number=number)
    category = get_object_or_404(Category, pk=category_id)
    return render(
        request, "tables/category_products.html", {"table": table, "category": category}
    )
