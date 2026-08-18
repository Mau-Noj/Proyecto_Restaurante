from django.db import migrations

BAR_CATEGORIES = ["Bebidas Sin Alcohol", "Bebidas Alcohólicas"]


def set_bar_station(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(name__in=BAR_CATEGORIES).update(station="BAR")


def revert(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(name__in=BAR_CATEGORIES).update(station="COCINA")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_category_station"),
    ]

    operations = [
        migrations.RunPython(set_bar_station, revert),
    ]
