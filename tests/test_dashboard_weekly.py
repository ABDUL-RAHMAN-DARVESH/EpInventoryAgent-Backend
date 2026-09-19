"""
Coverage for the Dashboard's weekly (Saturday -> Friday) financial window:
the week-boundary math itself, that Net Position/Receivables/Payables are
collected/paid amounts scoped to payments dated within the current week
(while the pending totals and owing counts cover everything unpaid to date), and the previous week's export + its 2-day expiry.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.dashboard_service import EXPORT_GRACE_DAYS, _previous_week_window, _week_bounds


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.parametrize(
    "reference,expected_start,expected_end",
    [
        (date(2026, 9, 12), date(2026, 9, 12), date(2026, 9, 18)),  # a Saturday -- first day of its week
        (date(2026, 9, 13), date(2026, 9, 12), date(2026, 9, 18)),  # the following Sunday
        (date(2026, 9, 18), date(2026, 9, 12), date(2026, 9, 18)),  # the following Friday -- last day of the week
        (date(2026, 9, 19), date(2026, 9, 19), date(2026, 9, 25)),  # the next Saturday -- a fresh week
    ],
)
def test_week_bounds_runs_saturday_to_friday(reference, expected_start, expected_end):
    week_start, week_end = _week_bounds(reference)
    assert week_start == expected_start
    assert week_end == expected_end
    assert week_start.weekday() == 5  # Saturday
    assert week_end.weekday() == 4  # Friday


def test_previous_week_window_is_exactly_the_week_before():
    today = date(2026, 9, 12)  # a Saturday -- first day of a new week
    prev_start, prev_end, days_since = _previous_week_window(today)
    assert prev_start == date(2026, 9, 5)
    assert prev_end == date(2026, 9, 11)
    assert days_since == 1


def test_export_grace_window_is_exactly_two_days():
    # Saturday (day 1 after last week ended) and Sunday (day 2) are both
    # within the grace window; Monday (day 3) is not.
    saturday, sunday, monday = date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14)

    _, _, days_since_sat = _previous_week_window(saturday)
    _, _, days_since_sun = _previous_week_window(sunday)
    _, _, days_since_mon = _previous_week_window(monday)

    assert 1 <= days_since_sat <= EXPORT_GRACE_DAYS
    assert 1 <= days_since_sun <= EXPORT_GRACE_DAYS
    assert not (1 <= days_since_mon <= EXPORT_GRACE_DAYS)


async def _create_customer(client, name, area="WeeklyArea"):
    resp = await client.post("/customers", json={"name": name, "area": area})
    assert resp.status_code == 201
    return resp.json()


async def _create_product(client, sku):
    resp = await client.post("/products", json={"sku": sku, "name": "Weekly Widget", "brand": "Generic"})
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_pending_receivables_cover_all_unpaid_sales_not_just_this_week(client):
    # Unlike the collected total (which is a per-week cash-flow figure), the
    # *pending* receivables and the "N customers still owe" count are not
    # weekly: an unpaid sale from a previous week is still money owed today.
    suffix = _unique()
    customer = await _create_customer(client, f"Weekly Customer{suffix}")
    product = await _create_product(client, f"WW{suffix}")

    before = (await client.get("/dashboard")).json()
    last_week_date = (date.fromisoformat(before["week_start"]) - timedelta(days=7)).isoformat()

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "sale_date": last_week_date,
            "items": [{"product_id": product["id"], "unit_price": "500.00", "quantity": 1}],
        },
    )
    assert resp.status_code == 201
    old_sale = resp.json()

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "300.00", "quantity": 1}],
        },
    )
    assert resp.status_code == 201

    after = (await client.get("/dashboard")).json()

    # Both the last-week sale and this week's sale count toward what's owed,
    # and it's one customer regardless of how many unpaid sales they have.
    assert Decimal(after["pending_receivables"]) - Decimal(before["pending_receivables"]) == Decimal("800.00")
    assert after["customers_with_outstanding_balance"] - before["customers_with_outstanding_balance"] == 1
    assert "overdue_customer_balance" not in after
    assert "overdue_manufacturer_balance" not in after

    # Paying the older sale off clears its 500 from what's owed, but the
    # customer still owes on this week's sale, so they stay in the count.
    resp = await client.post(f"/sales/{old_sale['id']}/payments", json={"amount": "500.00"})
    assert resp.status_code == 201
    paid = (await client.get("/dashboard")).json()
    assert Decimal(paid["pending_receivables"]) - Decimal(before["pending_receivables"]) == Decimal("300.00")
    assert paid["customers_with_outstanding_balance"] - before["customers_with_outstanding_balance"] == 1


@pytest.mark.asyncio
async def test_pending_payables_cover_all_unpaid_purchases_not_just_this_week(client):
    suffix = _unique()
    manufacturer = (await client.post("/manufacturers", json={"name": f"Weekly Manufacturer{suffix}"})).json()
    product = await _create_product(client, f"WP{suffix}")

    before = (await client.get("/dashboard")).json()
    last_week_date = (date.fromisoformat(before["week_start"]) - timedelta(days=7)).isoformat()

    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "purchase_date": last_week_date,
            "items": [{"product_id": product["id"], "quantity": 2, "line_total": "1000.00"}],
        },
    )
    assert resp.status_code == 201
    purchase = resp.json()

    after = (await client.get("/dashboard")).json()
    assert Decimal(after["pending_payables"]) - Decimal(before["pending_payables"]) == Decimal("1000.00")
    assert after["manufacturers_with_outstanding_balance"] - before["manufacturers_with_outstanding_balance"] == 1

    # Once fully paid, the manufacturer drops out of the "still owed" count.
    resp = await client.post(f"/purchases/{purchase['id']}/payments", json={"amount": "1000.00"})
    assert resp.status_code == 201
    paid = (await client.get("/dashboard")).json()
    assert Decimal(paid["pending_payables"]) == Decimal(before["pending_payables"])
    assert paid["manufacturers_with_outstanding_balance"] == before["manufacturers_with_outstanding_balance"]


@pytest.mark.asyncio
async def test_total_receivables_reflects_payments_dated_this_week_not_sale_date(client):
    # total_receivables is actual money collected -- scoped by the *payment's*
    # date, regardless of when the underlying sale happened.
    suffix = _unique()
    customer = await _create_customer(client, f"Weekly Customer{suffix}")
    product = await _create_product(client, f"WW{suffix}")

    before = (await client.get("/dashboard")).json()
    last_week_date = (date.fromisoformat(before["week_start"]) - timedelta(days=7)).isoformat()

    sale = (
        await client.post(
            "/sales",
            json={
                "customer_id": customer["id"],
                "sale_date": last_week_date,
                "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            },
        )
    ).json()

    # A payment dated last week must not count toward this week's total.
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "200.00", "payment_date": last_week_date})
    assert resp.status_code == 201

    # A payment dated this week (the default) must count.
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "300.00"})
    assert resp.status_code == 201

    after = (await client.get("/dashboard")).json()
    assert Decimal(after["total_receivables"]) - Decimal(before["total_receivables"]) == Decimal("300.00")


@pytest.mark.asyncio
async def test_initial_sale_payment_counts_as_receivable_but_not_as_cp_activity(client):
    # An advance/full payment taken at sale time is real money collected, so
    # it must count toward total_receivables -- but it is not a Customer
    # Payment collection visit, so it must never appear in (or become "the
    # latest" for) latest_customer_payments.
    suffix = _unique()
    customer = await _create_customer(client, f"Weekly Customer{suffix}")
    product = await _create_product(client, f"WW{suffix}")

    before = (await client.get("/dashboard")).json()

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            "initial_payment": {"amount": "400.00"},
        },
    )
    assert resp.status_code == 201

    after = (await client.get("/dashboard")).json()
    assert Decimal(after["total_receivables"]) - Decimal(before["total_receivables"]) == Decimal("400.00")

    latest_cp = after["latest_customer_payments"]
    if latest_cp is not None:
        assert all(p["customer_id"] != customer["id"] for p in latest_cp["payments"])


@pytest.mark.asyncio
async def test_previous_week_export_route_matches_availability_flag(client):
    dash = (await client.get("/dashboard")).json()
    resp = await client.get("/dashboard/weekly-export/previous")

    if dash["previous_week_export"]["available"]:
        assert resp.status_code == 200
        body = resp.json()
        assert body["week_start"] == dash["previous_week_export"]["week_start"]
        assert body["week_end"] == dash["previous_week_export"]["week_end"]
        assert "sales" in body and "purchases" in body
    else:
        assert resp.status_code == 404
