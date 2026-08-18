import pytest
from django.urls import reverse


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin1", email="admin1@example.com", password="s3cret-pass", is_staff=True
    )


@pytest.fixture
def employee_user(django_user_model):
    return django_user_model.objects.create_user(
        username="empleado1", email="empleado1@example.com", password="s3cret-pass"
    )


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login_admin"))


@pytest.mark.django_db
def test_dashboard_rejects_non_staff(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login_admin"))


@pytest.mark.django_db
def test_dashboard_renders_for_staff(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 200
    assert "Mesas y Salón" in response.content.decode()
