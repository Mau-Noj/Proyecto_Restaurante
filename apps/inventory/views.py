from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required
from apps.catalog.models import Product

from .forms import IngredientForm, RecipeItemFormSet, StockEntryForm, StockExitForm
from .models import Ingredient, StockMovement
from .services import register_movement


@staff_required
def index(request):
    return render(request, "inventory/index.html")


@staff_required
def ingredient_list(request):
    ingredients = Ingredient.objects.all()
    return render(
        request,
        "inventory/ingredient_list.html",
        {
            "ingredients": ingredients,
            "chart_labels": [ingredient.name for ingredient in ingredients],
            "chart_stock": [float(ingredient.stock) for ingredient in ingredients],
            "chart_min_stock": [float(ingredient.min_stock) for ingredient in ingredients],
            "chart_status": [ingredient.status for ingredient in ingredients],
        },
    )


@staff_required
def ingredient_create(request):
    if request.method == "POST":
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingrediente creado.")
            return redirect(reverse("inventory:ingredient_list"))
    else:
        form = IngredientForm()
    return render(
        request, "inventory/ingredient_form.html", {"form": form, "title": "Nuevo Ingrediente"}
    )


@staff_required
def ingredient_edit(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == "POST":
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingrediente actualizado.")
            return redirect(reverse("inventory:ingredient_list"))
    else:
        form = IngredientForm(instance=ingredient)
    return render(
        request,
        "inventory/ingredient_form.html",
        {"form": form, "title": "Editar Ingrediente", "ingredient": ingredient},
    )


@staff_required
def stock_entry(request):
    if request.method == "POST":
        form = StockEntryForm(request.POST)
        if form.is_valid():
            register_movement(
                ingredient=form.cleaned_data["ingredient"],
                movement_type=StockMovement.MovementType.COMPRA,
                quantity=form.cleaned_data["quantity"],
                created_by=request.user,
                reference=form.cleaned_data["reference"],
            )
            messages.success(request, "Entrada registrada.")
            return redirect(reverse("inventory:kardex"))
    else:
        form = StockEntryForm()
    return render(request, "inventory/stock_entry.html", {"form": form})


@staff_required
def stock_exit(request):
    if request.method == "POST":
        form = StockExitForm(request.POST)
        if form.is_valid():
            register_movement(
                ingredient=form.cleaned_data["ingredient"],
                movement_type=form.cleaned_data["movement_type"],
                quantity=form.cleaned_data["quantity"],
                created_by=request.user,
                reference=form.cleaned_data["reference"],
            )
            messages.success(request, "Salida registrada.")
            return redirect(reverse("inventory:kardex"))
    else:
        form = StockExitForm()
    return render(request, "inventory/stock_exit.html", {"form": form})


@staff_required
def kardex(request):
    movements = StockMovement.objects.select_related("ingredient", "created_by")
    return render(request, "inventory/kardex.html", {"movements": movements})


@staff_required
def recipe_list(request):
    products = Product.objects.select_related("category").prefetch_related("recipe_items")
    return render(request, "inventory/recipe_list.html", {"products": products})


@staff_required
def recipe_edit(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        formset = RecipeItemFormSet(request.POST, instance=product)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Receta actualizada.")
            return redirect(reverse("inventory:recipe_list"))
    else:
        formset = RecipeItemFormSet(instance=product)
    breadcrumb = f"Inventario / Recetas / {product.name}"
    return render(
        request,
        "inventory/recipe_edit.html",
        {"formset": formset, "product": product, "breadcrumb": breadcrumb},
    )


@staff_required
def cost_report(request):
    products = Product.objects.select_related("category").prefetch_related(
        "recipe_items__ingredient"
    )
    rows = []
    chart_labels = []
    chart_costs = []
    chart_prices = []
    chart_utilities = []
    for product in products:
        recipe_items = list(product.recipe_items.all())
        if recipe_items:
            cost = sum(ri.quantity * ri.ingredient.unit_cost for ri in recipe_items)
            utility = product.price - cost
            chart_labels.append(product.name)
            chart_costs.append(float(cost))
            chart_prices.append(float(product.price))
            chart_utilities.append(float(utility))
        else:
            cost = None
            utility = None
        rows.append({"product": product, "cost": cost, "utility": utility})
    return render(
        request,
        "inventory/cost_report.html",
        {
            "rows": rows,
            "chart_labels": chart_labels,
            "chart_costs": chart_costs,
            "chart_prices": chart_prices,
            "chart_utilities": chart_utilities,
        },
    )
