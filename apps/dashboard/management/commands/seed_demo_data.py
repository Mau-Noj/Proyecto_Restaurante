from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Product
from apps.employees.forms import generate_temp_password, generate_unique_username
from apps.employees.models import Employee
from apps.inventory.models import Ingredient, RecipeItem
from apps.payments.models import Bill, PaymentSplit
from apps.tables.models import Table

User = get_user_model()

DEMO_EMPLOYEES = [
    ("Ana", "López", "ana.lopez@example.com", Employee.Position.MESERO),
    ("Diego", "Ruiz", "diego.ruiz@example.com", Employee.Position.COCINERO),
    ("Sofía", "Ramírez", "sofia.ramirez@example.com", Employee.Position.CAJERO),
    ("Luis", "García", "luis.garcia@example.com", Employee.Position.GERENTE),
    ("María", "Torres", "maria.torres@example.com", Employee.Position.HOSTESS),
]

DEMO_INGREDIENTS = [
    # name, unit, stock, min_stock, unit_cost
    ("Masa de Pizza", Ingredient.Unit.KG, "2", "5", "15.00"),
    ("Salsa de Tomate", Ingredient.Unit.L, "3", "5", "20.00"),
    ("Queso Mozzarella", Ingredient.Unit.KG, "12", "5", "45.00"),
    ("Pepperoni", Ingredient.Unit.KG, "1", "4", "60.00"),
    ("Piña", Ingredient.Unit.KG, "6", "3", "18.00"),
    ("Jamón", Ingredient.Unit.KG, "2.5", "4", "35.00"),
    ("Papa", Ingredient.Unit.KG, "20", "8", "6.00"),
    ("Aceite", Ingredient.Unit.L, "4", "6", "18.00"),
    ("Queso Cheddar", Ingredient.Unit.KG, "5", "3", "50.00"),
    ("Agua Embotellada", Ingredient.Unit.UNIDAD, "50", "20", "3.00"),
    ("Gaseosa Embotellada", Ingredient.Unit.UNIDAD, "30", "20", "4.50"),
    ("Cerveza Embotellada", Ingredient.Unit.UNIDAD, "15", "20", "8.00"),
    ("Vino (botella)", Ingredient.Unit.UNIDAD, "3", "10", "40.00"),
]

# producto, [(ingrediente, cantidad), ...]
DEMO_RECIPES = {
    "Pizza Pepperoni": [
        ("Masa de Pizza", "0.30"),
        ("Salsa de Tomate", "0.15"),
        ("Queso Mozzarella", "0.20"),
        ("Pepperoni", "0.10"),
    ],
    "Pizza Hawaiana": [
        ("Masa de Pizza", "0.30"),
        ("Salsa de Tomate", "0.15"),
        ("Queso Mozzarella", "0.20"),
        ("Piña", "0.10"),
        ("Jamón", "0.10"),
    ],
    "Papas Fritas": [
        ("Papa", "0.25"),
        ("Aceite", "0.05"),
    ],
    "Papas con Queso": [
        ("Papa", "0.25"),
        ("Aceite", "0.05"),
        ("Queso Cheddar", "0.10"),
    ],
    "Agua Pura": [("Agua Embotellada", "1")],
    "Gaseosa": [("Gaseosa Embotellada", "1")],
    "Cerveza": [("Cerveza Embotellada", "1")],
    "Vino Tinto (copa)": [("Vino (botella)", "0.15")],
}


class Command(BaseCommand):
    help = (
        "Crea empleados, ingredientes/recetas y cuentas pagadas de muestra, para poder "
        "ver poblados los reportes y graficas del panel. Seguro de correr mas de una vez."
    )

    def handle(self, *args, **options):
        employees = self._seed_employees()
        self._seed_ingredients_and_recipes()
        self._seed_bills(employees)
        self.stdout.write(self.style.SUCCESS("Datos de muestra listos."))

    def _seed_employees(self):
        employees = {}
        for first_name, last_name, email, position in DEMO_EMPLOYEES:
            existing = Employee.objects.filter(user__email=email).select_related("user").first()
            if existing:
                employees[position] = existing.user
                continue
            username = generate_unique_username(first_name, last_name)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=generate_temp_password(),
                must_change_password=False,
            )
            Employee.objects.create(
                user=user, position=position, hire_date=timezone.localdate()
            )
            employees[position] = user
            self.stdout.write(f"Empleado creado: {username} ({position})")
        return employees

    def _seed_ingredients_and_recipes(self):
        ingredients = {}
        for name, unit, stock, min_stock, unit_cost in DEMO_INGREDIENTS:
            ingredient, created = Ingredient.objects.get_or_create(
                name=name,
                defaults={
                    "unit": unit,
                    "stock": Decimal(stock),
                    "min_stock": Decimal(min_stock),
                    "unit_cost": Decimal(unit_cost),
                },
            )
            ingredients[name] = ingredient
            if created:
                self.stdout.write(f"Ingrediente creado: {name}")

        for product_name, items in DEMO_RECIPES.items():
            try:
                product = Product.objects.get(name=product_name)
            except Product.DoesNotExist:
                continue
            for ingredient_name, quantity in items:
                RecipeItem.objects.get_or_create(
                    product=product,
                    ingredient=ingredients[ingredient_name],
                    defaults={"quantity": Decimal(quantity)},
                )

    def _seed_bills(self, employees):
        if Bill.objects.filter(closed_by__email="ana.lopez@example.com").exists():
            self.stdout.write("Cuentas de muestra ya existian, no se duplican.")
            return

        mesero = employees[Employee.Position.MESERO]
        cajero = employees[Employee.Position.CAJERO]
        now = timezone.now()

        mesa_bills = [
            (4, mesero, "170.00", "17.00", [(PaymentSplit.Method.EFECTIVO, "187.00")], now),
            (
                5,
                mesero,
                "105.00",
                "15.75",
                [
                    (PaymentSplit.Method.EFECTIVO, "60.75"),
                    (PaymentSplit.Method.TARJETA, "60.00"),
                ],
                now,
            ),
            (6, mesero, "245.00", "29.40", [(PaymentSplit.Method.TARJETA, "274.40")], now),
            (
                7,
                mesero,
                "90.00",
                "9.00",
                [(PaymentSplit.Method.TRANSFERENCIA, "99.00")],
                now - timedelta(days=1),
            ),
            (
                8,
                mesero,
                "310.00",
                "46.50",
                [(PaymentSplit.Method.PAGO_MOVIL, "356.50")],
                now - timedelta(days=2),
            ),
        ]
        for number, waiter, subtotal, tip, splits, closed_at in mesa_bills:
            table = Table.objects.get(number=number)
            bill = Bill.objects.create(
                table=table,
                bill_type=Bill.BillType.MESA,
                status=Bill.Status.PAGADA,
                subtotal=Decimal(subtotal),
                tip=Decimal(tip),
                total=Decimal(subtotal) + Decimal(tip),
                opened_by=waiter,
                closed_by=waiter,
                closed_at=closed_at,
            )
            for method, amount in splits:
                PaymentSplit.objects.create(bill=bill, method=method, amount=Decimal(amount))

        takeout_bills = [
            (cajero, "32.00", PaymentSplit.Method.EFECTIVO, now),
            (cajero, "55.00", PaymentSplit.Method.TARJETA, now - timedelta(days=1)),
        ]
        for cashier, subtotal, method, closed_at in takeout_bills:
            bill = Bill.objects.create(
                bill_type=Bill.BillType.LLEVAR,
                status=Bill.Status.PAGADA,
                subtotal=Decimal(subtotal),
                tip=Decimal("0"),
                total=Decimal(subtotal),
                opened_by=cashier,
                closed_by=cashier,
                closed_at=closed_at,
            )
            PaymentSplit.objects.create(bill=bill, method=method, amount=Decimal(subtotal))

        self.stdout.write(f"{len(mesa_bills) + len(takeout_bills)} cuentas de muestra creadas.")
