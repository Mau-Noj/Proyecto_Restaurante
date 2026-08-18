import datetime

import pytest
from django.core import mail
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
def employee_user(django_user_model):
    return django_user_model.objects.create_user(
        username="empleado1",
        email="empleado1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )


VALID_DATA = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana.perez@example.com",
    "phone": "555-1234",
    "position": Employee.Position.MESERO,
    "hire_date": "2026-01-15",
}


@pytest.mark.django_db
class TestEmployeeAccess:
    def test_list_requires_staff(self, client, employee_user):
        client.force_login(employee_user)
        response = client.get(reverse("employees:list"))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_admin"))

    def test_create_requires_staff(self, client):
        response = client.get(reverse("employees:create"))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_admin"))


@pytest.mark.django_db
class TestEmployeeCreate:
    def test_get_renders_form(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("employees:create"))
        assert response.status_code == 200

    def test_valid_post_creates_user_and_employee(self, client, staff_user, django_user_model):
        client.force_login(staff_user)
        response = client.post(reverse("employees:create"), VALID_DATA)

        assert response.status_code == 302
        assert response.url == reverse("employees:list")

        employee = Employee.objects.get(user__email="ana.perez@example.com")
        assert employee.user.username == "ana.perez"
        assert employee.user.first_name == "Ana"
        assert employee.user.is_staff is False
        assert employee.user.has_usable_password()
        assert employee.position == Employee.Position.MESERO
        assert employee.hire_date == datetime.date(2026, 1, 15)
        assert employee.user.must_change_password is True

    def test_welcome_email_is_sent(self, client, staff_user):
        client.force_login(staff_user)
        client.post(reverse("employees:create"), VALID_DATA)

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["ana.perez@example.com"]
        assert "ana.perez" in sent.body

    def test_username_collision_gets_suffixed(self, client, staff_user, django_user_model):
        client.force_login(staff_user)
        django_user_model.objects.create_user(username="ana.perez", email="other@example.com")

        client.post(reverse("employees:create"), VALID_DATA)

        employee = Employee.objects.get(user__email="ana.perez@example.com")
        assert employee.user.username == "ana.perez2"

    def test_duplicate_email_rejected(self, client, staff_user, django_user_model):
        client.force_login(staff_user)
        django_user_model.objects.create_user(username="existing", email="ana.perez@example.com")

        response = client.post(reverse("employees:create"), VALID_DATA)

        assert response.status_code == 200
        assert response.context["form"].errors
        assert Employee.objects.count() == 0


@pytest.mark.django_db
def test_list_shows_created_employee(client, staff_user, django_user_model):
    client.force_login(staff_user)
    client.post(reverse("employees:create"), VALID_DATA)

    response = client.get(reverse("employees:list"))

    assert response.status_code == 200
    assert "ana.perez" in response.content.decode()
