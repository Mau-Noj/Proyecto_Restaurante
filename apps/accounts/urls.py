from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/admin/", views.AdminLoginView.as_view(), name="login_admin"),
    path("login/empleado/", views.EmployeeLoginView.as_view(), name="login_empleado"),
    path("logout/", views.ThemedLogoutView.as_view(), name="logout"),
    path("empleado/", views.employee_home, name="employee_home"),
    path(
        "cambiar-password/",
        views.ForcedPasswordChangeView.as_view(),
        name="change_password",
    ),
]
