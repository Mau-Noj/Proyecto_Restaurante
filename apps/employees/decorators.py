from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def position_required(*positions):
    """Exige sesión iniciada y que el Employee tenga uno de los puestos dados.

    El Gerente/Administrador (y cualquier superusuario) siempre pasa, sin
    importar los puestos pedidos: necesita poder supervisar cualquier
    pantalla operativa (KDS, caja, etc.), no solo la de su propio puesto.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="accounts:login_empleado")
        def wrapped(request, *args, **kwargs):
            from .models import Employee

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            employee = getattr(request.user, "employee_profile", None)
            if not employee:
                return redirect("accounts:login_empleado")
            if employee.position != Employee.Position.GERENTE and employee.position not in positions:
                return redirect("accounts:login_empleado")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
