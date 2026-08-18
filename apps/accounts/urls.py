from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/admin/", views.AdminLoginView.as_view(), name="login_admin"),
    path("login/empleado/", views.EmployeeLoginView.as_view(), name="login_empleado"),
    path("logout/", LogoutView.as_view(next_page="accounts:login_empleado"), name="logout"),
    path("empleado/", views.employee_home, name="employee_home"),
    path(
        "cambiar-password/",
        views.ForcedPasswordChangeView.as_view(),
        name="change_password",
    ),
]
