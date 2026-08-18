from django.shortcuts import redirect
from django.urls import Resolver404, resolve

# Vistas a las que un usuario con must_change_password=True SI puede entrar,
# para no quedar atrapado sin poder cerrar sesión o cambiar la contraseña.
EXEMPT_URL_NAMES = {
    "accounts:change_password",
    "accounts:logout",
    "accounts:login_admin",
    "accounts:login_empleado",
    "healthz",
}


class ForcePasswordChangeMiddleware:
    """Si el usuario tiene must_change_password=True, lo manda a cambiarla
    antes de dejarlo usar cualquier otra pantalla."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and not request.path.startswith("/static/")
            and not request.path.startswith("/admin/")
        ):
            try:
                match = resolve(request.path)
                current = (
                    f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
                )
            except Resolver404:
                current = None
            if current not in EXEMPT_URL_NAMES:
                return redirect("accounts:change_password")
        return self.get_response(request)
