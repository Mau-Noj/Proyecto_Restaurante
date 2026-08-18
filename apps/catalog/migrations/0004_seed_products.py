from decimal import Decimal

from django.db import migrations

# Fotos de relleno de Wikimedia Commons (licencia libre, enlace estable via
# Special:FilePath) mientras no haya fotos reales de los productos.
PRODUCTS = {
    "Bebidas Sin Alcohol": [
        ("Agua Pura", "10.00", "https://commons.wikimedia.org/wiki/Special:FilePath/Bottled_water.jpg"),
        (
            "Gaseosa",
            "12.00",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Soda_Cans_Pexels_Breakingpic_3008.jpg",
        ),
    ],
    "Bebidas Alcohólicas": [
        ("Cerveza", "20.00", "https://commons.wikimedia.org/wiki/Special:FilePath/Heineken_Bottle.jpg"),
        (
            "Vino Tinto (copa)",
            "35.00",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Glass_of_red_wine.jpg",
        ),
    ],
    "Pizza": [
        ("Pizza Pepperoni", "85.00", "https://commons.wikimedia.org/wiki/Special:FilePath/Pepperoni_pizza.jpg"),
        ("Pizza Hawaiana", "80.00", "https://commons.wikimedia.org/wiki/Special:FilePath/Hawaiian_pizza_1.jpg"),
    ],
    "Papas": [
        ("Papas Fritas", "25.00", "https://commons.wikimedia.org/wiki/Special:FilePath/French_Fries.JPG"),
        (
            "Papas con Queso",
            "35.00",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Shake_shack_cheese_fries.jpg",
        ),
    ],
}


def seed_products(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    for category_name, items in PRODUCTS.items():
        category = Category.objects.get(name=category_name)
        for order, (name, price, image_url) in enumerate(items):
            Product.objects.get_or_create(
                category=category,
                name=name,
                defaults={"price": Decimal(price), "image_url": image_url, "order": order},
            )


def unseed_products(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    all_names = [name for items in PRODUCTS.values() for name, _, _ in items]
    Product.objects.filter(name__in=all_names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_product"),
    ]

    operations = [
        migrations.RunPython(seed_products, unseed_products),
    ]
