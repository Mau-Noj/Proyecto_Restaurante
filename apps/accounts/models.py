from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Fija AUTH_USER_MODEL desde el inicio del proyecto.

    Sin campos de rol/permiso todavía: eso llega con el módulo AUTH (RBAC).
    """

    email = models.EmailField(unique=True)
    must_change_password = models.BooleanField(
        "Debe cambiar la contraseña",
        default=True,
        help_text="Se exige cambiarla en el primer inicio de sesión (contraseña temporal).",
    )
