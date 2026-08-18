from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.index, name="index"),
    path("ingredientes/", views.ingredient_list, name="ingredient_list"),
    path("ingredientes/nuevo/", views.ingredient_create, name="ingredient_create"),
    path("ingredientes/<int:pk>/editar/", views.ingredient_edit, name="ingredient_edit"),
    path("entradas/nueva/", views.stock_entry, name="stock_entry"),
    path("salidas/nueva/", views.stock_exit, name="stock_exit"),
    path("movimientos/", views.kardex, name="kardex"),
    path("recetas/", views.recipe_list, name="recipe_list"),
    path("recetas/<int:product_id>/", views.recipe_edit, name="recipe_edit"),
    path("costos/", views.cost_report, name="cost_report"),
]
