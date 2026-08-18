from django.db import migrations

TOTAL_TABLES = 10


def seed_tables(apps, schema_editor):
    Table = apps.get_model("tables", "Table")
    Table.objects.bulk_create(
        [Table(number=n) for n in range(1, TOTAL_TABLES + 1)],
        ignore_conflicts=True,
    )


def unseed_tables(apps, schema_editor):
    Table = apps.get_model("tables", "Table")
    Table.objects.filter(number__range=(1, TOTAL_TABLES)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tables", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tables, unseed_tables),
    ]
