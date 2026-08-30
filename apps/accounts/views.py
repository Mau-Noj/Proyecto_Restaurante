from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import AdminAuthenticationForm, ThemedPasswordChangeForm


def _employee_landing_url(user) -> str:
    """A dónde debe caer un empleado no-admin justo después de loguearse
    (o de cambiar su contraseña temporal), según su puesto."""
    from apps.employees.models import Employee  # import local: evita acoplar accounts a employees

    employee = getattr(user, "employee_profile", None)
    if employee:
        if employee.position == Employee.Position.MESERO:
            return str(reverse_lazy("tables:select"))
        if employee.position == Employee.Position.COCINERO:
            return str(reverse_lazy("kds:kitchen"))
        if employee.position == Employee.Position.BARTENDER:
            return str(reverse_lazy("kds:bar"))
        if employee.position == Employee.Position.CAJERO:
            return str(reverse_lazy("payments:takeout_new"))
        if employee.position == Employee.Position.KIOSKO:
            return str(reverse_lazy("attendance:display"))
    return str(reverse_lazy("accounts:employee_home"))


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
        # Respeta ?next= cuando viene de un login_required puntual (ej. al
        # escanear el QR de asistencia sin sesión abierta) para no perder a
        # dónde iba; si no hay next, cae al landing normal por puesto.
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return _employee_landing_url(self.request.user)


class ThemedLogoutView(LogoutView):
    """Manda al login de Admin a quien salía del panel, y al de Empleado a
    los demás - next_page es estático, así que hay que decidirlo antes de
    que dispatch() cierre la sesión y pierda request.user."""

    def dispatch(self, request, *args, **kwargs):
        self._was_staff = request.user.is_authenticated and request.user.is_staff
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        if getattr(self, "_was_staff", False):
            return str(reverse_lazy("accounts:login_admin"))
        return str(reverse_lazy("accounts:login_empleado"))


@login_required(login_url="accounts:login_empleado")
def employee_home(request):
    # Si alguien cae directo en esta URL (favorito viejo, escrita a mano)
    # en vez de pasar por el login, igual lo manda a su landing por puesto
    # -- si no, se queda viendo la pantalla generica "sin modulos" aunque
    # su puesto si tenga una pantalla propia (ej. Kiosko).
    landing = _employee_landing_url(request.user)
    if landing != str(reverse_lazy("accounts:employee_home")):
        return redirect(landing)
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
        return _employee_landing_url(self.request.user)
