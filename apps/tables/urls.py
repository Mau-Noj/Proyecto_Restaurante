from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("", views.table_select, name="select"),
    path("<int:number>/", views.table_detail, name="detail"),
]
