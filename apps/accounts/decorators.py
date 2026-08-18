from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test


def _is_staff(user):
    return user.is_staff


def staff_required(view_func):
    """Exige sesión iniciada y is_staff=True; si no, manda al login de admin."""

    @wraps(view_func)
    @login_required(login_url="accounts:login_admin")
    @user_passes_test(_is_staff, login_url="accounts:login_admin")
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return wrapped
