from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.urls import reverse_lazy

from .forms import AdminAuthenticationForm


class AdminLoginView(LoginView):
    template_name = "accounts/login_admin.html"
    authentication_form = AdminAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy("admin:index"))


class EmployeeLoginView(LoginView):
    template_name = "accounts/login_empleado.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy("accounts:employee_home"))


@login_required(login_url="accounts:login_empleado")
def employee_home(request):
    return render(request, "accounts/employee_home.html")
