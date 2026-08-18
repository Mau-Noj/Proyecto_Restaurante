from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import staff_required

from .forms import (
    ConfirmPasswordForm,
    EmployeeCreateForm,
    EmployeeEditForm,
    reset_employee_password,
)
from .models import Employee


@staff_required
def employee_list(request):
    employees = Employee.objects.select_related("user").all()
    new_credentials = request.session.pop("new_credentials", None)

    position_labels = dict(Employee.Position.choices)
    position_counts = (
        Employee.objects.values("position").annotate(count=Count("id")).order_by("-count")
    )
    return render(
        request,
        "employees/list.html",
        {
            "employees": employees,
            "new_credentials": new_credentials,
            "chart_labels": [position_labels[row["position"]] for row in position_counts],
            "chart_data": [row["count"] for row in position_counts],
        },
    )


@staff_required
def employee_create(request):
    if request.method == "POST":
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            employee, temp_password = form.save()
            request.session["new_credentials"] = {
                "heading": "Empleado creado",
                "username": employee.user.username,
                "password": temp_password,
            }
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
        request.session["new_credentials"] = {
            "heading": "Contraseña restablecida",
            "username": employee.user.username,
            "password": temp_password,
        }
    return redirect(reverse("employees:list"))


@staff_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = ConfirmPasswordForm(request.POST, user=request.user)
        if form.is_valid():
            full_name = employee.user.get_full_name()
            employee.user.delete()  # cascada: borra tambien el Employee
            messages.success(request, f"Se eliminó a {full_name}.")
            return redirect(reverse("employees:list"))
    else:
        form = ConfirmPasswordForm(user=request.user)
    return render(request, "employees/delete.html", {"form": form, "employee": employee})
