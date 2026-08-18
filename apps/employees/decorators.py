from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def position_required(*positions):
    """Exige sesión iniciada y que el Employee tenga uno de los puestos dados."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="accounts:login_empleado")
        def wrapped(request, *args, **kwargs):
            employee = getattr(request.user, "employee_profile", None)
            if not employee or employee.position not in positions:
                return redirect("accounts:login_empleado")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
