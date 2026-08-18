import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required

from .emails import send_welcome_email
from .forms import EmployeeCreateForm
from .models import Employee

logger = logging.getLogger(__name__)


@staff_required
def employee_list(request):
    employees = Employee.objects.select_related("user").all()
    return render(request, "employees/list.html", {"employees": employees})


@staff_required
def employee_create(request):
    if request.method == "POST":
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            employee, temp_password = form.save()

            try:
                send_welcome_email(employee, temp_password)
                email_note = f"Se envió un correo a {employee.user.email} con sus credenciales."
            except Exception:
                logger.exception(
                    "No se pudo enviar el correo de bienvenida a %s", employee.user.email
                )
                email_note = "No se pudo enviar el correo — compártelas manualmente:"

            messages.success(
                request,
                f"Empleado creado. {email_note} Usuario: {employee.user.username} · "
                f"Contraseña temporal: {temp_password}",
            )
            return redirect(reverse("employees:list"))
    else:
        form = EmployeeCreateForm()
    return render(request, "employees/create.html", {"form": form})
