from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import render
from django.urls import reverse_lazy

from .forms import AdminAuthenticationForm, ThemedPasswordChangeForm


class AdminLoginView(LoginView):
    template_name = "accounts/login_admin.html"
    authentication_form = AdminAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy("dashboard:index"))


class EmployeeLoginView(LoginView):
    template_name = "accounts/login_empleado.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy("accounts:employee_home"))


@login_required(login_url="accounts:login_empleado")
def employee_home(request):
    return render(request, "accounts/employee_home.html")


class ForcedPasswordChangeView(PasswordChangeView):
    template_name = "accounts/change_password.html"
    form_class = ThemedPasswordChangeForm
    login_url = "accounts:login_empleado"

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=["must_change_password"])
        return response

    def get_success_url(self):
        if self.request.user.is_staff:
            return str(reverse_lazy("dashboard:index"))
        return str(reverse_lazy("accounts:employee_home"))
