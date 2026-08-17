from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Fija AUTH_USER_MODEL desde el inicio del proyecto.

    Sin campos de rol/permiso todavía: eso llega con el módulo AUTH (RBAC).
    """

    email = models.EmailField(unique=True)
