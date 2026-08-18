import pytest
from django.urls import reverse


@pytest.fixture
def temp_password_staff(django_user_model):
    return django_user_model.objects.create_user(
        username="admin1",
        email="admin1@example.com",
        password="temp-pass-123",
        is_staff=True,
    )  # must_change_password=True por defecto


@pytest.fixture
def temp_password_employee(django_user_model):
    return django_user_model.objects.create_user(
        username="empleado1",
        email="empleado1@example.com",
        password="temp-pass-123",
    )  # must_change_password=True por defecto


@pytest.mark.django_db
def test_user_with_temp_password_is_redirected_to_change_password(client, temp_password_staff):
    client.force_login(temp_password_staff)
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302
    assert response.url == reverse("accounts:change_password")


@pytest.mark.django_db
def test_change_password_page_itself_is_reachable(client, temp_password_staff):
    client.force_login(temp_password_staff)
    response = client.get(reverse("accounts:change_password"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_logout_is_reachable_even_with_temp_password(client, temp_password_staff):
    client.force_login(temp_password_staff)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_successful_change_clears_flag_and_redirects_staff_to_dashboard(
    client, temp_password_staff
):
    client.force_login(temp_password_staff)
    response = client.post(
        reverse("accounts:change_password"),
        {
            "old_password": "temp-pass-123",
            "new_password1": "una-nueva-clave-segura-99",
            "new_password2": "una-nueva-clave-segura-99",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:index")

    temp_password_staff.refresh_from_db()
    assert temp_password_staff.must_change_password is False
    assert temp_password_staff.check_password("una-nueva-clave-segura-99")


@pytest.mark.django_db
def test_successful_change_redirects_employee_to_employee_home(client, temp_password_employee):
    client.force_login(temp_password_employee)
    response = client.post(
        reverse("accounts:change_password"),
        {
            "old_password": "temp-pass-123",
            "new_password1": "una-nueva-clave-segura-99",
            "new_password2": "una-nueva-clave-segura-99",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:employee_home")

    temp_password_employee.refresh_from_db()
    assert temp_password_employee.must_change_password is False


@pytest.mark.django_db
def test_wrong_old_password_does_not_clear_flag(client, temp_password_staff):
    client.force_login(temp_password_staff)
    response = client.post(
        reverse("accounts:change_password"),
        {
            "old_password": "wrong-password",
            "new_password1": "una-nueva-clave-segura-99",
            "new_password2": "una-nueva-clave-segura-99",
        },
    )
    assert response.status_code == 200
    temp_password_staff.refresh_from_db()
    assert temp_password_staff.must_change_password is True
