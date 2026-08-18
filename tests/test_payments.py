from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.models import Product
from apps.employees.models import Employee
from apps.payments.models import Bill, PaymentSplit
from apps.payments.services import close_bill, open_bill_for_table, set_tip
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
def cajero_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="cajero1",
        email="cajero1@example.com",
        password="s3cret-pass",
        must_change_password=False,
    )
    Employee.objects.create(user=user, position=Employee.Position.CAJERO, hire_date="2026-01-01")
    return user


def _send_order(client, table_number, product):
    client.post(
        reverse("tables:cart_increment", args=[table_number, product.category_id, product.pk])
    )
    client.post(reverse("tables:submit_order", args=[table_number]))


@pytest.mark.django_db
class TestOpenBillForTable:
    def test_aggregates_subtotal_and_marks_cuenta_pedida(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        _send_order(client, 1, pizza)

        table = Table.objects.get(number=1)
        bill = open_bill_for_table(table, mesero_user)

        assert bill.subtotal == pizza.price
        assert bill.total == pizza.price
        table.refresh_from_db()
        assert table.status == Table.Status.CUENTA_PEDIDA

    def test_reopens_same_bill_and_aggregates_new_rounds(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        water = Product.objects.get(name="Agua Pura")
        table = Table.objects.get(number=2)

        _send_order(client, 2, pizza)
        first_bill = open_bill_for_table(table, mesero_user)

        table.status = Table.Status.OCUPADA
        table.save(update_fields=["status"])
        _send_order(client, 2, water)
        second_bill = open_bill_for_table(table, mesero_user)

        assert first_bill.pk == second_bill.pk
        assert second_bill.subtotal == pizza.price + water.price


@pytest.mark.django_db
class TestBillTipAndSplits:
    def test_set_tip_updates_total(self, staff_user):
        table = Table.objects.get(number=3)
        bill = Bill.objects.create(
            table=table, bill_type=Bill.BillType.MESA, opened_by=staff_user, subtotal=Decimal("100")
        )
        set_tip(bill, Decimal("15.00"))
        bill.refresh_from_db()
        assert bill.tip == Decimal("15.00")
        assert bill.total == Decimal("115.00")

    def test_set_tip_view_applies_preset(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        _send_order(client, 3, pizza)
        table = Table.objects.get(number=3)
        bill = open_bill_for_table(table, mesero_user)

        client.post(reverse("payments:set_bill_tip", args=[bill.pk]), {"preset": "10"})

        bill.refresh_from_db()
        expected_tip = (pizza.price * Decimal("10") / Decimal("100")).quantize(Decimal("0.01"))
        assert bill.tip == expected_tip

    def test_balance_due_tracks_splits(self, staff_user):
        table = Table.objects.get(number=4)
        bill = Bill.objects.create(
            table=table,
            bill_type=Bill.BillType.MESA,
            opened_by=staff_user,
            subtotal=Decimal("100"),
            total=Decimal("100"),
        )
        PaymentSplit.objects.create(
            bill=bill, label="Persona 1", method=PaymentSplit.Method.EFECTIVO, amount=Decimal("40")
        )
        assert bill.paid_amount == Decimal("40")
        assert bill.balance_due == Decimal("60")

        PaymentSplit.objects.create(
            bill=bill, label="Persona 2", method=PaymentSplit.Method.TARJETA, amount=Decimal("60")
        )
        assert bill.balance_due == Decimal("0")


@pytest.mark.django_db
class TestCloseBill:
    def test_closing_a_table_bill_frees_it_for_cleaning(self, staff_user):
        table = Table.objects.get(number=5)
        table.status = Table.Status.CUENTA_PEDIDA
        table.save(update_fields=["status"])
        bill = Bill.objects.create(
            table=table,
            bill_type=Bill.BillType.MESA,
            opened_by=staff_user,
            subtotal=Decimal("50"),
            total=Decimal("50"),
        )
        close_bill(bill, staff_user)

        bill.refresh_from_db()
        table.refresh_from_db()
        assert bill.status == Bill.Status.PAGADA
        assert bill.closed_by == staff_user
        assert table.status == Table.Status.LIMPIEZA

    def test_closing_a_takeout_bill_does_not_touch_any_table(self, staff_user):
        bill = Bill.objects.create(
            bill_type=Bill.BillType.LLEVAR,
            opened_by=staff_user,
            subtotal=Decimal("10"),
            total=Decimal("10"),
        )
        close_bill(bill, staff_user)
        bill.refresh_from_db()
        assert bill.status == Bill.Status.PAGADA


@pytest.mark.django_db
class TestBillDetailViewFlow:
    def test_confirm_blocked_until_balance_covered(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        _send_order(client, 6, pizza)
        table = Table.objects.get(number=6)
        bill = open_bill_for_table(table, mesero_user)

        response = client.post(reverse("payments:confirm_bill", args=[bill.pk]))
        assert response.status_code == 302
        bill.refresh_from_db()
        assert bill.status == Bill.Status.ABIERTA

    def test_confirm_succeeds_once_covered(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        _send_order(client, 7, pizza)
        table = Table.objects.get(number=7)
        bill = open_bill_for_table(table, mesero_user)

        client.post(
            reverse("payments:add_bill_split", args=[bill.pk]),
            {
                "label": "Persona 1",
                "method": PaymentSplit.Method.EFECTIVO,
                "amount": str(bill.total),
            },
        )
        response = client.post(reverse("payments:confirm_bill", args=[bill.pk]))

        assert response.status_code == 302
        assert response.url == reverse("tables:select")
        bill.refresh_from_db()
        table.refresh_from_db()
        assert bill.status == Bill.Status.PAGADA
        assert table.status == Table.Status.LIMPIEZA

    def test_cancel_table_bill_reverts_to_ocupada(self, client, mesero_user):
        client.force_login(mesero_user)
        pizza = Product.objects.get(name="Pizza Pepperoni")
        _send_order(client, 8, pizza)
        table = Table.objects.get(number=8)
        open_bill_for_table(table, mesero_user)

        client.post(reverse("payments:cancel_table_bill", args=[8]))

        table.refresh_from_db()
        assert table.status == Table.Status.OCUPADA


@pytest.mark.django_db
class TestMarkTableClean:
    def test_frees_table_only_when_in_cleaning(self, client, mesero_user):
        client.force_login(mesero_user)
        table = Table.objects.get(number=9)
        table.status = Table.Status.LIMPIEZA
        table.save(update_fields=["status"])

        client.post(reverse("tables:mark_clean", args=[9]))

        table.refresh_from_db()
        assert table.status == Table.Status.LIBRE

    def test_does_nothing_when_not_in_cleaning(self, client, mesero_user):
        client.force_login(mesero_user)
        table = Table.objects.get(number=10)
        table.status = Table.Status.OCUPADA
        table.save(update_fields=["status"])

        client.post(reverse("tables:mark_clean", args=[10]))

        table.refresh_from_db()
        assert table.status == Table.Status.OCUPADA


@pytest.mark.django_db
class TestTakeoutFlow:
    def test_mesero_cannot_access_caja(self, client, mesero_user):
        client.force_login(mesero_user)
        response = client.get(reverse("payments:takeout_new"))
        assert response.status_code == 302
        assert response.url == reverse("accounts:login_empleado")

    def test_checkout_creates_order_without_table_and_opens_bill(self, client, cajero_user):
        client.force_login(cajero_user)
        water = Product.objects.get(name="Agua Pura")

        client.post(
            reverse("payments:takeout_cart_increment", args=[water.category_id, water.pk])
        )
        response = client.post(reverse("payments:takeout_checkout"))

        assert response.status_code == 302
        bill = Bill.objects.get(bill_type=Bill.BillType.LLEVAR)
        assert bill.table is None
        assert bill.subtotal == water.price
        order = bill.orders.get()
        assert order.table is None
        assert order.created_by == cajero_user

    def test_confirming_takeout_bill_returns_to_new_order_screen(self, client, cajero_user):
        client.force_login(cajero_user)
        water = Product.objects.get(name="Agua Pura")
        client.post(
            reverse("payments:takeout_cart_increment", args=[water.category_id, water.pk])
        )
        client.post(reverse("payments:takeout_checkout"))
        bill = Bill.objects.get(bill_type=Bill.BillType.LLEVAR)

        client.post(
            reverse("payments:add_bill_split", args=[bill.pk]),
            {"label": "", "method": PaymentSplit.Method.EFECTIVO, "amount": str(bill.total)},
        )
        response = client.post(reverse("payments:confirm_bill", args=[bill.pk]))

        assert response.url == reverse("payments:takeout_new")
        bill.refresh_from_db()
        assert bill.status == Bill.Status.PAGADA


@pytest.mark.django_db
class TestReports:
    def test_reports_require_staff(self, client, mesero_user):
        client.force_login(mesero_user)
        for url_name in ("report_by_waiter", "report_shift", "report_audit"):
            response = client.get(reverse(f"payments:{url_name}"))
            assert response.status_code == 302

    def test_report_by_waiter_shows_totals(self, client, staff_user):
        table = Table.objects.get(number=1)
        bill = Bill.objects.create(
            table=table,
            bill_type=Bill.BillType.MESA,
            opened_by=staff_user,
            subtotal=Decimal("100"),
            tip=Decimal("10"),
            total=Decimal("110"),
        )
        close_bill(bill, staff_user)

        client.force_login(staff_user)
        response = client.get(reverse("payments:report_by_waiter"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Q100" in content or "Q100.00" in content

    def test_report_shift_filters_by_date(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("payments:report_shift"))
        assert response.status_code == 200

    def test_report_audit_renders_charts(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("payments:report_audit"))
        assert response.status_code == 200
        assert "chart-labels" in response.content.decode()
