import pytest
from django.urls import reverse

from apps.employees.models import Employee


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin1",
        email="admin1@example.com",
        password="s3cret-pass",
        is_staff=True,
        must_change_password=False,
    )


@pytest.fixture
def employee(django_user_model):
    user = django_user_model.objects.create_user(
        username="ana.perez",
        email="ana.perez@example.com",
        first_name="Ana",
        last_name="Pérez",
        password="old-temp-pass",
    )
    return Employee.objects.create(
        user=user, phone="555-0000", position=Employee.Position.MESERO, hire_date="2026-01-01"
    )


@pytest.mark.django_db
class TestEmployeeEdit:
    def test_requires_staff(self, client, employee):
        response = client.get(reverse("employees:edit", args=[employee.pk]))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_admin"))

    def test_get_prefills_form(self, client, staff_user, employee):
        client.force_login(staff_user)
        response = client.get(reverse("employees:edit", args=[employee.pk]))
        assert response.status_code == 200
        assert response.context["form"].initial["email"] == "ana.perez@example.com"

    def test_valid_post_updates_employee_and_user(self, client, staff_user, employee):
        client.force_login(staff_user)
        response = client.post(
            reverse("employees:edit", args=[employee.pk]),
            {
                "first_name": "Ana María",
                "last_name": "Pérez",
                "email": "ana.perez@example.com",
                "phone": "555-9999",
                "position": Employee.Position.CAJERO,
                "hire_date": "2026-01-01",
                "is_active": "on",
            },
        )
        assert response.status_code == 302
        assert response.url == reverse("employees:list")

        employee.refresh_from_db()
        assert employee.user.first_name == "Ana María"
        assert employee.phone == "555-9999"
        assert employee.position == Employee.Position.CAJERO
        assert employee.user.is_active is True

    def test_unchecking_is_active_deactivates_account(self, client, staff_user, employee):
        client.force_login(staff_user)
        client.post(
            reverse("employees:edit", args=[employee.pk]),
            {
                "first_name": employee.user.first_name,
                "last_name": employee.user.last_name,
                "email": employee.user.email,
                "phone": employee.phone,
                "position": employee.position,
                "hire_date": str(employee.hire_date),
                # is_active omitido a propósito: un checkbox sin marcar no se envía
            },
        )
        employee.refresh_from_db()
        assert employee.user.is_active is False

    def test_deactivated_employee_cannot_log_in(self, client, staff_user, employee):
        employee.user.is_active = False
        employee.user.save(update_fields=["is_active"])

        response = client.post(
            reverse("accounts:login_empleado"),
            {"username": "ana.perez", "password": "old-temp-pass"},
        )
        assert response.status_code == 200
        assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
class TestEmployeeResetPassword:
    def test_requires_staff(self, client, employee):
        response = client.post(reverse("employees:reset_password", args=[employee.pk]))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_admin"))

    def test_reset_generates_new_password_and_forces_change(self, client, staff_user, employee):
        client.force_login(staff_user)
        old_password_hash = employee.user.password

        response = client.post(reverse("employees:reset_password", args=[employee.pk]))

        assert response.status_code == 302
        assert response.url == reverse("employees:list")

        employee.refresh_from_db()
        assert employee.user.password != old_password_hash
        assert employee.user.must_change_password is True
        assert not employee.user.check_password("old-temp-pass")
