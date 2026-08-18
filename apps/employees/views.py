from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required

from .forms import EmployeeCreateForm
from .models import Employee


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
            messages.success(
                request,
                f"Empleado creado. Usuario: {employee.user.username} · "
                f"Contraseña temporal: {temp_password}",
            )
            return redirect(reverse("employees:list"))
    else:
        form = EmployeeCreateForm()
    return render(request, "employees/create.html", {"form": form})
