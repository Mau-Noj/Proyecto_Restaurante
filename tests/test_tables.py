import pytest
from django.urls import reverse

from apps.tables.models import Table


@pytest.fixture
def employee_user(django_user_model):
    return django_user_model.objects.create_user(
        username="empleado1",
        email="empleado1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )


@pytest.mark.django_db
def test_ten_tables_are_seeded_by_migration():
    assert Table.objects.count() == 10
    assert list(Table.objects.values_list("number", flat=True)) == list(range(1, 11))


@pytest.mark.django_db
def test_select_requires_login(client):
    response = client.get(reverse("tables:select"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login_empleado"))


@pytest.mark.django_db
def test_select_lists_all_tables(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse("tables:select"))
    assert response.status_code == 200
    content = response.content.decode()
    for number in range(1, 11):
        assert f">{number}<" in content


@pytest.mark.django_db
def test_detail_requires_login(client):
    response = client.get(reverse("tables:detail", args=[1]))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login_empleado"))


@pytest.mark.django_db
def test_detail_shows_selected_table(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse("tables:detail", args=[7]))
    assert response.status_code == 200
    assert "7" in response.content.decode()


@pytest.mark.django_db
def test_detail_404_for_unknown_table(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse("tables:detail", args=[99]))
    assert response.status_code == 404
