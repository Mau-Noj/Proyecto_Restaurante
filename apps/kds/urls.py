from django.urls import path

from . import views

app_name = "kds"

urlpatterns = [
    path("cocina/", views.kitchen_display, name="kitchen"),
    path("bar/", views.bar_display, name="bar"),
    path("empezar/<int:item_id>/", views.start_preparing, name="start_preparing"),
    path("entregar/<int:item_id>/", views.mark_delivered, name="mark_delivered"),
    path("reportes/tiempos/", views.report_prep_times, name="report_prep_times"),
]
