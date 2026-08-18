import pytest

from apps.catalog.models import Category


@pytest.mark.django_db
def test_categories_are_seeded_by_migration():
    names = list(Category.objects.order_by("order").values_list("name", flat=True))
    assert names == ["Bebidas Sin Alcohol", "Bebidas Alcohólicas", "Pizza", "Papas"]
