from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class AdminAuthenticationForm(AuthenticationForm):
    """Igual que el login normal, pero exige que la cuenta sea de staff."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                _("Esta cuenta no tiene permisos de administrador."),
                code="not_staff",
            )
