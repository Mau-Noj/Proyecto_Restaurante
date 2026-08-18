from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required

from .forms import EmployeeCreateForm, EmployeeEditForm, reset_employee_password
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
                extra_tags="credentials",
            )
            return redirect(reverse("employees:list"))
    else:
        form = EmployeeCreateForm()
    return render(request, "employees/create.html", {"form": form})


@staff_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = EmployeeEditForm(request.POST, employee=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado actualizado.")
            return redirect(reverse("employees:list"))
    else:
        form = EmployeeEditForm(employee=employee)
    return render(request, "employees/edit.html", {"form": form, "employee": employee})


@staff_required
def employee_reset_password(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        temp_password = reset_employee_password(employee)
        messages.success(
            request,
            f"Contraseña restablecida. Usuario: {employee.user.username} · "
            f"Contraseña temporal: {temp_password}",
            extra_tags="credentials",
        )
    return redirect(reverse("employees:list"))
