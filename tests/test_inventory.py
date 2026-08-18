from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.models import Product
from apps.inventory.models import Ingredient, RecipeItem, StockMovement
from apps.inventory.services import discount_recipe_for_order, register_movement
from apps.orders.models import Order, OrderItem
from apps.tables.models import Table


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


@pytest.fixture
def harina(db):
    return Ingredient.objects.create(
        name="Harina", unit=Ingredient.Unit.KG, stock=10, min_stock=5, unit_cost=Decimal("8.00")
    )


@pytest.mark.django_db
class TestIngredientStatus:
    def test_safe_when_well_above_minimum(self):
        ingredient = Ingredient(stock=10, min_stock=5)
        assert ingredient.status == "SEGURO"

    def test_low_when_at_or_below_minimum(self):
        ingredient = Ingredient(stock=4, min_stock=5)
        assert ingredient.status == "BAJO"

    def test_critical_when_at_or_below_half_minimum(self):
        ingredient = Ingredient(stock=2, min_stock=5)
        assert ingredient.status == "CRITICO"

    def test_critical_when_zero_or_negative(self):
        ingredient = Ingredient(stock=0, min_stock=5)
        assert ingredient.status == "CRITICO"


@pytest.mark.django_db
class TestRegisterMovement:
    def test_compra_increases_stock(self, harina, staff_user):
        register_movement(
            ingredient=harina,
            movement_type=StockMovement.MovementType.COMPRA,
            quantity=Decimal("5"),
            created_by=staff_user,
            reference="Factura 001",
        )
        harina.refresh_from_db()
        assert harina.stock == Decimal("15")
        movement = StockMovement.objects.get(ingredient=harina)
        assert movement.movement_type == StockMovement.MovementType.COMPRA
        assert movement.reference == "Factura 001"

    def test_merma_decreases_stock(self, harina, staff_user):
        register_movement(
            ingredient=harina,
            movement_type=StockMovement.MovementType.MERMA,
            quantity=Decimal("3"),
            created_by=staff_user,
        )
        harina.refresh_from_db()
        assert harina.stock == Decimal("7")


@pytest.mark.django_db
class TestDiscountRecipeForOrder:
    def test_deducts_stock_for_each_ingredient_in_recipe(self, staff_user):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        dough = Ingredient.objects.create(
            name="Masa", unit=Ingredient.Unit.G, stock=1000, min_stock=200
        )
        cheese = Ingredient.objects.create(
            name="Mozzarella", unit=Ingredient.Unit.G, stock=500, min_stock=100
        )
        RecipeItem.objects.create(product=pizza, ingredient=dough, quantity=150)
        RecipeItem.objects.create(product=pizza, ingredient=cheese, quantity=120)

        table = Table.objects.get(number=1)
        order = Order.objects.create(table=table, created_by=staff_user)
        OrderItem.objects.create(order=order, product=pizza, quantity=2)

        discount_recipe_for_order(order, staff_user)

        dough.refresh_from_db()
        cheese.refresh_from_db()
        assert dough.stock == Decimal("700")
        assert cheese.stock == Decimal("260")
        venta_count = StockMovement.objects.filter(
            movement_type=StockMovement.MovementType.VENTA
        ).count()
        assert venta_count == 2

    def test_product_without_recipe_does_not_error(self, staff_user):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        table = Table.objects.get(number=1)
        order = Order.objects.create(table=table, created_by=staff_user)
        OrderItem.objects.create(order=order, product=pizza, quantity=1)

        discount_recipe_for_order(order, staff_user)

        assert StockMovement.objects.count() == 0


@pytest.mark.django_db
class TestIngredientViews:
    def test_list_requires_staff(self, client, employee_user):
        client.force_login(employee_user)
        response = client.get(reverse("inventory:ingredient_list"))
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login_admin"))

    def test_list_shows_ingredients_and_status(self, client, staff_user, harina):
        client.force_login(staff_user)
        response = client.get(reverse("inventory:ingredient_list"))
        assert response.status_code == 200
        assert "Harina" in response.content.decode()

    def test_create_ingredient(self, client, staff_user):
        client.force_login(staff_user)
        response = client.post(
            reverse("inventory:ingredient_create"),
            {
                "name": "Pepperoni",
                "unit": Ingredient.Unit.G,
                "stock": "500",
                "min_stock": "100",
                "unit_cost": "0.15",
            },
        )
        assert response.status_code == 302
        assert Ingredient.objects.filter(name="Pepperoni").exists()

    def test_edit_ingredient(self, client, staff_user, harina):
        client.force_login(staff_user)
        response = client.post(
            reverse("inventory:ingredient_edit", args=[harina.pk]),
            {
                "name": "Harina",
                "unit": Ingredient.Unit.KG,
                "stock": "20",
                "min_stock": "5",
                "unit_cost": "8.00",
            },
        )
        assert response.status_code == 302
        harina.refresh_from_db()
        assert harina.stock == Decimal("20")


@pytest.mark.django_db
class TestStockEntryExitViews:
    def test_stock_entry_registers_compra(self, client, staff_user, harina):
        client.force_login(staff_user)
        response = client.post(
            reverse("inventory:stock_entry"),
            {"ingredient": harina.pk, "quantity": "5", "reference": "Distribuidora XYZ"},
        )
        assert response.status_code == 302
        harina.refresh_from_db()
        assert harina.stock == Decimal("15")

    def test_stock_exit_registers_merma(self, client, staff_user, harina):
        client.force_login(staff_user)
        response = client.post(
            reverse("inventory:stock_exit"),
            {
                "ingredient": harina.pk,
                "movement_type": StockMovement.MovementType.MERMA,
                "quantity": "2",
                "reference": "Se cayó el saco",
            },
        )
        assert response.status_code == 302
        harina.refresh_from_db()
        assert harina.stock == Decimal("8")

    def test_kardex_lists_movements(self, client, staff_user, harina):
        register_movement(
            ingredient=harina,
            movement_type=StockMovement.MovementType.COMPRA,
            quantity=Decimal("5"),
            created_by=staff_user,
        )
        client.force_login(staff_user)
        response = client.get(reverse("inventory:kardex"))
        assert response.status_code == 200
        assert "Harina" in response.content.decode()


@pytest.mark.django_db
class TestRecipeViews:
    def test_recipe_list_requires_staff(self, client, employee_user):
        client.force_login(employee_user)
        response = client.get(reverse("inventory:recipe_list"))
        assert response.status_code == 302

    def test_recipe_edit_saves_items(self, client, staff_user, harina):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        client.force_login(staff_user)
        response = client.post(
            reverse("inventory:recipe_edit", args=[pizza.pk]),
            {
                "recipe_items-TOTAL_FORMS": "1",
                "recipe_items-INITIAL_FORMS": "0",
                "recipe_items-MIN_NUM_FORMS": "0",
                "recipe_items-MAX_NUM_FORMS": "1000",
                "recipe_items-0-ingredient": harina.pk,
                "recipe_items-0-quantity": "150",
                "recipe_items-0-id": "",
            },
        )
        assert response.status_code == 302
        assert RecipeItem.objects.filter(product=pizza, ingredient=harina).exists()


@pytest.mark.django_db
class TestCostReport:
    def test_shows_cost_and_utility_when_recipe_exists(self, client, staff_user, harina):
        pizza = Product.objects.get(name="Pizza Pepperoni")
        RecipeItem.objects.create(product=pizza, ingredient=harina, quantity=Decimal("2"))

        client.force_login(staff_user)
        response = client.get(reverse("inventory:cost_report"))

        assert response.status_code == 200
        row = next(r for r in response.context["rows"] if r["product"] == pizza)
        assert row["cost"] == harina.unit_cost * 2
        assert row["utility"] == pizza.price - (harina.unit_cost * 2)

    def test_shows_no_recipe_for_products_without_one(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("inventory:cost_report"))
        assert "Sin receta asignada" in response.content.decode()
