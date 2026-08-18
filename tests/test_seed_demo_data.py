import pytest
from django.core.management import call_command

from apps.employees.models import Employee
from apps.inventory.models import Ingredient, RecipeItem
from apps.payments.models import Bill


@pytest.mark.django_db
def test_seed_demo_data_creates_expected_records():
    call_command("seed_demo_data")

    assert Employee.objects.filter(position=Employee.Position.CAJERO).exists()
    assert Employee.objects.filter(position=Employee.Position.GERENTE).exists()
    assert Ingredient.objects.count() == 13
    assert RecipeItem.objects.exists()
    assert Bill.objects.filter(status=Bill.Status.PAGADA).count() >= 7


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent():
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Employee.objects.filter(user__email="ana.lopez@example.com").count() == 1
    assert Ingredient.objects.filter(name="Masa de Pizza").count() == 1
