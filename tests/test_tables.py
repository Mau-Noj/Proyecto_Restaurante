from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.models import Category, Product
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


@pytest.mark.django_db
def test_detail_shows_menu_categories(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse("tables:detail", args=[3]))
    assert response.status_code == 200
    content = response.content.decode()
    for name in ["Bebidas Sin Alcohol", "Bebidas Alcohólicas", "Pizza", "Papas"]:
        assert name in content


@pytest.mark.django_db
def test_category_products_requires_login(client):
    category = Category.objects.first()
    response = client.get(reverse("tables:category_products", args=[1, category.pk]))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login_empleado"))


@pytest.mark.django_db
def test_category_products_shows_table_and_category(client, employee_user):
    client.force_login(employee_user)
    category = Category.objects.get(name="Pizza")

    response = client.get(reverse("tables:category_products", args=[5, category.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Pizza" in content
    assert "Mesa 5" in content


@pytest.mark.django_db
def test_category_products_shows_category_menu_overlay(client, employee_user):
    client.force_login(employee_user)
    category = Category.objects.get(name="Pizza")

    response = client.get(reverse("tables:category_products", args=[5, category.pk]))

    content = response.content.decode()
    assert "category-menu-overlay" in content
    for name in ["Bebidas Sin Alcohol", "Bebidas Alcohólicas", "Pizza", "Papas"]:
        assert name in content


@pytest.mark.django_db
def test_category_products_404_for_unknown_table_or_category(client, employee_user):
    client.force_login(employee_user)
    category = Category.objects.first()

    response = client.get(reverse("tables:category_products", args=[99, category.pk]))
    assert response.status_code == 404

    response = client.get(reverse("tables:category_products", args=[1, 999]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_category_products_shows_zero_quantity_initially(client, employee_user):
    client.force_login(employee_user)
    pizza = Category.objects.get(name="Pizza")

    response = client.get(reverse("tables:category_products", args=[2, pizza.pk]))

    assert response.status_code == 200
    assert response.context["products"][0]["quantity"] == 0


@pytest.mark.django_db
class TestCart:
    def test_increment_requires_login(self, client):
        product = Product.objects.first()
        response = client.post(
            reverse("tables:cart_increment", args=[1, product.category_id, product.pk])
        )
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_empleado"))

    def test_increment_increases_quantity(self, client, employee_user):
        client.force_login(employee_user)
        product = Product.objects.get(name="Pizza Pepperoni")

        client.post(
            reverse("tables:cart_increment", args=[4, product.category_id, product.pk])
        )
        client.post(
            reverse("tables:cart_increment", args=[4, product.category_id, product.pk])
        )

        response = client.get(reverse("tables:category_products", args=[4, product.category_id]))
        items = {i["product"].pk: i["quantity"] for i in response.context["products"]}
        assert items[product.pk] == 2

    def test_decrement_never_goes_below_zero(self, client, employee_user):
        client.force_login(employee_user)
        product = Product.objects.get(name="Pizza Pepperoni")

        client.post(
            reverse("tables:cart_decrement", args=[4, product.category_id, product.pk])
        )

        response = client.get(reverse("tables:category_products", args=[4, product.category_id]))
        items = {i["product"].pk: i["quantity"] for i in response.context["products"]}
        assert items[product.pk] == 0

    def test_cart_is_scoped_per_table(self, client, employee_user):
        client.force_login(employee_user)
        product = Product.objects.get(name="Pizza Pepperoni")

        client.post(
            reverse("tables:cart_increment", args=[1, product.category_id, product.pk])
        )

        response = client.get(reverse("tables:category_products", args=[2, product.category_id]))
        items = {i["product"].pk: i["quantity"] for i in response.context["products"]}
        assert items[product.pk] == 0


@pytest.mark.django_db
class TestPreorder:
    def test_requires_login(self, client):
        response = client.get(reverse("tables:preorder", args=[1]))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_empleado"))

    def test_empty_cart_shows_empty_state(self, client, employee_user):
        client.force_login(employee_user)
        response = client.get(reverse("tables:preorder", args=[6]))
        assert response.status_code == 200
        assert response.context["lines"] == []
        assert response.context["total"] == Decimal("0")

    def test_shows_category_menu_overlay(self, client, employee_user):
        client.force_login(employee_user)
        response = client.get(reverse("tables:preorder", args=[6]))
        content = response.content.decode()
        assert "category-menu-overlay" in content
        assert "Pizza" in content

    def test_shows_added_products_with_total(self, client, employee_user):
        client.force_login(employee_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        water = Product.objects.get(name="Agua Pura")

        client.post(reverse("tables:cart_increment", args=[8, pizza.category_id, pizza.pk]))
        client.post(reverse("tables:cart_increment", args=[8, water.category_id, water.pk]))
        client.post(reverse("tables:cart_increment", args=[8, water.category_id, water.pk]))

        response = client.get(reverse("tables:preorder", args=[8]))

        assert response.status_code == 200
        lines = {line["product"].pk: line["quantity"] for line in response.context["lines"]}
        assert lines[pizza.pk] == 1
        assert lines[water.pk] == 2
        assert response.context["total"] == pizza.price + (water.price * 2)
