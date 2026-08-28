from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.index, name="index"),
    path("mesa/<int:number>/cobrar/", views.open_table_bill, name="open_table_bill"),
    path("mesa/<int:number>/cancelar-cobro/", views.cancel_table_bill, name="cancel_table_bill"),
    path("cuenta/<int:pk>/", views.bill_detail, name="bill_detail"),
    path("cuenta/<int:pk>/propina/", views.set_bill_tip, name="set_bill_tip"),
    path("cuenta/<int:pk>/descuento/", views.set_bill_discount, name="set_bill_discount"),
    path("cuenta/<int:pk>/pagos/agregar/", views.add_bill_split, name="add_bill_split"),
    path(
        "cuenta/<int:pk>/pagos/<int:split_id>/eliminar/",
        views.remove_bill_split,
        name="remove_bill_split",
    ),
    path("cuenta/<int:pk>/confirmar/", views.confirm_bill, name="confirm_bill"),
    path("caja/nuevo/", views.takeout_new, name="takeout_new"),
    path(
        "caja/categoria/<int:category_id>/",
        views.takeout_category_products,
        name="takeout_category_products",
    ),
    path(
        "caja/categoria/<int:category_id>/producto/<int:product_id>/sumar/",
        views.takeout_cart_increment,
        name="takeout_cart_increment",
    ),
    path(
        "caja/categoria/<int:category_id>/producto/<int:product_id>/restar/",
        views.takeout_cart_decrement,
        name="takeout_cart_decrement",
    ),
    path("caja/carrito/", views.takeout_cart_view, name="takeout_cart"),
    path("caja/cobrar/", views.takeout_checkout, name="takeout_checkout"),
    path("reportes/meseros/", views.report_by_waiter, name="report_by_waiter"),
    path("reportes/turno/", views.report_shift, name="report_shift"),
    path("reportes/auditoria/", views.report_audit, name="report_audit"),
    path("reportes/platillos/", views.report_top_products, name="report_top_products"),
]
