import pytest
from django.urls import reverse

from apps.catalog.models import Product
from apps.employees.models import Employee
from apps.orders.models import Order, OrderItem
from apps.tables.models import Table


@pytest.fixture
def cocinero_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="cocinero1",
        email="cocinero1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )
    Employee.objects.create(user=user, position=Employee.Position.COCINERO, hire_date="2026-01-01")
    return user


@pytest.fixture
def bartender_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="bartender1",
        email="bartender1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )
    Employee.objects.create(
        user=user, position=Employee.Position.BARTENDER, hire_date="2026-01-01"
    )
    return user


@pytest.fixture
def mesero_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="mesero1",
        email="mesero1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )
    Employee.objects.create(user=user, position=Employee.Position.MESERO, hire_date="2026-01-01")
    return user


@pytest.fixture
def order_with_items(cocinero_user):
    table = Table.objects.get(number=3)
    order = Order.objects.create(table=table, created_by=cocinero_user)
    pizza = Product.objects.get(name="Pizza Pepperoni")
    beer = Product.objects.get(name="Cerveza")
    OrderItem.objects.create(order=order, product=pizza, quantity=2)
    OrderItem.objects.create(order=order, product=beer, quantity=1)
    return order


@pytest.mark.django_db
class TestKitchenDisplay:
    def test_requires_login(self, client):
        response = client.get(reverse("kds:kitchen"))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_empleado"))

    def test_mesero_cannot_access(self, client, mesero_user):
        client.force_login(mesero_user)
        response = client.get(reverse("kds:kitchen"))
        assert response.status_code == 302
        assert response.url == reverse("accounts:login_empleado")

    def test_bartender_cannot_access_kitchen(self, client, bartender_user):
        client.force_login(bartender_user)
        response = client.get(reverse("kds:kitchen"))
        assert response.status_code == 302
        assert response.url == reverse("accounts:login_empleado")

    def test_shows_only_kitchen_items(self, client, cocinero_user, order_with_items):
        client.force_login(cocinero_user)
        response = client.get(reverse("kds:kitchen"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Pizza Pepperoni" in content
        assert "Cerveza" not in content
        assert "Mesa" in content
        assert ">3<" in content

    def test_only_oldest_pending_item_is_highlighted(self, client, cocinero_user):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        table = Table.objects.get(number=1)
        order = Order.objects.create(table=table, created_by=cocinero_user)
        OrderItem.objects.create(order=order, product=pizza, quantity=1)
        OrderItem.objects.create(order=order, product=pizza, quantity=1)

        client.force_login(cocinero_user)
        response = client.get(reverse("kds:kitchen"))

        assert response.content.decode().count("border-emerald-400/60") == 1

    def test_shows_takeout_orders_without_a_table(self, client, cocinero_user):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        order = Order.objects.create(table=None, created_by=cocinero_user)
        OrderItem.objects.create(order=order, product=pizza, quantity=1)

        client.force_login(cocinero_user)
        response = client.get(reverse("kds:kitchen"))

        assert response.status_code == 200
        assert "Para Llevar" in response.content.decode()


@pytest.mark.django_db
class TestBarDisplay:
    def test_cocinero_cannot_access_bar(self, client, cocinero_user):
        client.force_login(cocinero_user)
        response = client.get(reverse("kds:bar"))
        assert response.status_code == 302
        assert response.url == reverse("accounts:login_empleado")

    def test_shows_only_bar_items(self, client, bartender_user, order_with_items):
        client.force_login(bartender_user)
        response = client.get(reverse("kds:bar"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Cerveza" in content
        assert "Pizza Pepperoni" not in content


@pytest.mark.django_db
class TestMarkDelivered:
    def test_marks_item_delivered_and_removes_from_pending(
        self, client, cocinero_user, order_with_items
    ):
        client.force_login(cocinero_user)
        item = order_with_items.items.get(product__name="Pizza Pepperoni")

        response = client.post(reverse("kds:mark_delivered", args=[item.pk]))

        assert response.status_code == 302
        assert response.url == reverse("kds:kitchen")

        item.refresh_from_db()
        assert item.status == OrderItem.Status.ENTREGADO
        assert item.delivered_at is not None

        response = client.get(reverse("kds:kitchen"))
        assert "Pizza Pepperoni" not in response.content.decode()

    def test_delivering_bar_item_redirects_to_bar(
        self, client, bartender_user, order_with_items
    ):
        client.force_login(bartender_user)
        item = order_with_items.items.get(product__name="Cerveza")

        response = client.post(reverse("kds:mark_delivered", args=[item.pk]))

        assert response.url == reverse("kds:bar")
