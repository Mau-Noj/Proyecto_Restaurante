from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("", views.table_select, name="select"),
    path("<int:number>/", views.table_detail, name="detail"),
    path(
        "<int:number>/categoria/<int:category_id>/",
        views.category_products,
        name="category_products",
    ),
    path(
        "<int:number>/categoria/<int:category_id>/producto/<int:product_id>/sumar/",
        views.cart_increment,
        name="cart_increment",
    ),
    path(
        "<int:number>/categoria/<int:category_id>/producto/<int:product_id>/restar/",
        views.cart_decrement,
        name="cart_decrement",
    ),
    path("<int:number>/pre-orden/", views.preorder, name="preorder"),
]
