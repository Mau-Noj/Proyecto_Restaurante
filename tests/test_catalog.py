import pytest

from apps.catalog.models import Category, Product


@pytest.mark.django_db
def test_categories_are_seeded_by_migration():
    names = list(Category.objects.order_by("order").values_list("name", flat=True))
    assert names == ["Bebidas Sin Alcohol", "Bebidas Alcohólicas", "Pizza", "Papas"]


@pytest.mark.django_db
def test_products_are_seeded_by_migration():
    assert Product.objects.count() == 8
    pizza = Category.objects.get(name="Pizza")
    assert pizza.products.count() == 2
    assert pizza.products.filter(name="Pizza Pepperoni", price="85.00").exists()


@pytest.mark.django_db
def test_seeded_products_have_image_urls():
    assert not Product.objects.filter(image_url="").exists()
