from django.db import migrations

CATEGORIES = [
    "Bebidas Sin Alcohol",
    "Bebidas Alcohólicas",
    "Pizza",
    "Papas",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for order, name in enumerate(CATEGORIES):
        Category.objects.get_or_create(name=name, defaults={"order": order})


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(name__in=CATEGORIES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
