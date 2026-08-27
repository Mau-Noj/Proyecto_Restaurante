from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required

from .forms import CategoryForm, ProductForm
from .models import Category, Product


@staff_required
def index(request):
    return render(
        request,
        "catalog/index.html",
        {
            "category_count": Category.objects.count(),
            "product_count": Product.objects.count(),
        },
    )


@staff_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    return render(request, "catalog/category_list.html", {"categories": categories})


@staff_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada.")
            return redirect(reverse("catalog:category_list"))
    else:
        form = CategoryForm()
    return render(
        request, "catalog/category_form.html", {"form": form, "title": "Nueva Categoría"}
    )


@staff_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada.")
            return redirect(reverse("catalog:category_list"))
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        "catalog/category_form.html",
        {"form": form, "title": "Editar Categoría", "category": category},
    )


@staff_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        try:
            name = category.name
            category.delete()
            messages.success(request, f"Se eliminó la categoría {name}.")
            return redirect(reverse("catalog:category_list"))
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: uno de sus productos ya tiene pedidos registrados. "
                "Puedes editarla o vaciarla en vez de borrarla.",
            )
            return redirect(reverse("catalog:category_list"))
    return render(request, "catalog/category_delete.html", {"category": category})


@staff_required
def product_list(request):
    products = Product.objects.select_related("category").all()
    category_id = request.GET.get("categoria")
    if category_id:
        products = products.filter(category_id=category_id)
    return render(
        request,
        "catalog/product_list.html",
        {
            "products": products,
            "categories": Category.objects.all(),
            "selected_category": category_id,
        },
    )


@staff_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto agregado al menú.")
            return redirect(reverse("catalog:product_list"))
    else:
        form = ProductForm()
    return render(
        request, "catalog/product_form.html", {"form": form, "title": "Nuevo Producto"}
    )


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado.")
            return redirect(reverse("catalog:product_list"))
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        "catalog/product_form.html",
        {"form": form, "title": "Editar Producto", "product": product},
    )


@staff_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            name = product.name
            product.delete()
            messages.success(request, f"Se eliminó {name} del menú.")
            return redirect(reverse("catalog:product_list"))
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar {product.name}: ya tiene pedidos registrados. "
                "Si ya no se vende, considera quitarlo del menú de otra forma.",
            )
            return redirect(reverse("catalog:product_list"))
    return render(request, "catalog/product_delete.html", {"product": product})
