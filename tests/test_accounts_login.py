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
class TestAdminLogin:
    def test_get_renders_form(self, client):
        response = client.get(reverse("accounts:login_admin"))
        assert response.status_code == 200

    def test_valid_staff_login_redirects_to_admin_index(self, client, staff_user):
        response = client.post(
            reverse("accounts:login_admin"),
            {"username": "admin1", "password": "s3cret-pass"},
        )
        assert response.status_code == 302
        assert response.url == reverse("admin:index")

    def test_non_staff_user_is_rejected(self, client, employee_user):
        response = client.post(
            reverse("accounts:login_admin"),
            {"username": "empleado1", "password": "s3cret-pass"},
        )
        assert response.status_code == 200
        assert not response.wsgi_request.user.is_authenticated
        assert response.context["form"].errors

    def test_invalid_credentials_show_generic_error(self, client, staff_user):
        response = client.post(
            reverse("accounts:login_admin"),
            {"username": "admin1", "password": "wrong-password"},
        )
        assert response.status_code == 200
        assert not response.wsgi_request.user.is_authenticated
        assert response.context["form"].errors


@pytest.mark.django_db
class TestEmployeeLogin:
    def test_get_renders_form(self, client):
        response = client.get(reverse("accounts:login_empleado"))
        assert response.status_code == 200

    def test_valid_login_redirects_to_employee_home(self, client, employee_user):
        response = client.post(
            reverse("accounts:login_empleado"),
            {"username": "empleado1", "password": "s3cret-pass"},
        )
        assert response.status_code == 302
        assert response.url == reverse("accounts:employee_home")

    def test_employee_home_requires_login(self, client):
        response = client.get(reverse("accounts:employee_home"))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_empleado"))
