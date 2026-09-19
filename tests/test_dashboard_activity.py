"""
Coverage for the Dashboard's "latest sales visit" / "latest payment
collection round" aggregates -- these group sales/payments by (area, date)
using whichever area+date the most recently recorded row belongs to, matching
the real field workflow of visiting one area at a time.
"""
import uuid
from decimal import Decimal

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


async def _create_customer(client, name, area):
    resp = await client.post("/customers", json={"name": name, "area": area})
    assert resp.status_code == 201
    return resp.json()


async def _create_product(client, sku, name="Ceiling Fan"):
    resp = await client.post("/products", json={"sku": sku, "name": name, "brand": "Generic"})
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_latest_sales_activity_aggregates_the_most_recent_area_batch(client):
    suffix = _unique()
    area = f"Sector-{suffix}"
    product = await _create_product(client, f"FAN{suffix}")

    customer_a = await _create_customer(client, f"Customer A{suffix}", area)
    customer_b = await _create_customer(client, f"Customer B{suffix}", area)

    # Sale 1: fully paid via a full initial payment.
    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer_a["id"],
            "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            "initial_payment": {"amount": "1000.00"},
        },
    )
    assert resp.status_code == 201

    # Sale 2: partially paid.
    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer_b["id"],
            "items": [{"product_id": product["id"], "unit_price": "2000.00", "quantity": 1}],
            "initial_payment": {"amount": "500.00"},
        },
    )
    assert resp.status_code == 201

    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    latest = data["latest_sales"]
    assert latest is not None
    assert latest["area"] == area
    assert latest["sales_count"] == 2
    assert latest["customers_count"] == 2
    assert Decimal(latest["total_sales_amount"]) == Decimal("3000.00")
    assert Decimal(latest["total_advance_received"]) == Decimal("1500.00")
    assert Decimal(latest["total_fully_paid_amount"]) == Decimal("1000.00")
    assert latest["fully_paid_count"] == 1
    assert latest["fully_paid_customers_count"] == 1
    assert Decimal(latest["total_pending_amount"]) == Decimal("1500.00")
    assert latest["pending_count"] == 1
    assert len(latest["sales"]) == 2
    assert all(row["customer_name"] in (customer_a["name"], customer_b["name"]) for row in latest["sales"])
    # A sale row must never carry Customer Payment collection history --
    # that's a separate activity on a separate visit.
    assert all("payments" not in row for row in latest["sales"])


@pytest.mark.asyncio
async def test_latest_sales_activity_ignores_older_areas(client):
    suffix = _unique()
    old_area = f"OldArea-{suffix}"
    new_area = f"NewArea-{suffix}"
    product = await _create_product(client, f"FAN-OLD{suffix}")

    old_customer = await _create_customer(client, f"Old Customer{suffix}", old_area)
    resp = await client.post(
        "/sales",
        json={
            "customer_id": old_customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "100.00", "quantity": 1}],
        },
    )
    assert resp.status_code == 201

    new_customer = await _create_customer(client, f"New Customer{suffix}", new_area)
    resp = await client.post(
        "/sales",
        json={
            "customer_id": new_customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "250.00", "quantity": 1}],
        },
    )
    assert resp.status_code == 201

    resp = await client.get("/dashboard")
    latest = resp.json()["latest_sales"]
    assert latest["area"] == new_area
    assert latest["sales_count"] == 1
    assert Decimal(latest["total_sales_amount"]) == Decimal("250.00")


@pytest.mark.asyncio
async def test_latest_customer_payment_activity_aggregates_the_most_recent_area_round(client):
    suffix = _unique()
    area = f"CPArea-{suffix}"
    product = await _create_product(client, f"FAN-CP{suffix}")

    customer_a = await _create_customer(client, f"CP Customer A{suffix}", area)
    customer_b = await _create_customer(client, f"CP Customer B{suffix}", area)

    sale_a = (
        await client.post(
            "/sales",
            json={
                "customer_id": customer_a["id"],
                "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            },
        )
    ).json()
    sale_b = (
        await client.post(
            "/sales",
            json={
                "customer_id": customer_b["id"],
                "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            },
        )
    ).json()

    resp = await client.post(f"/sales/{sale_a['id']}/payments", json={"amount": "400.00"})
    assert resp.status_code == 201
    resp = await client.post(f"/sales/{sale_b['id']}/payments", json={"amount": "300.00"})
    assert resp.status_code == 201

    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    latest = resp.json()["latest_customer_payments"]
    assert latest is not None
    assert latest["area"] == area
    assert latest["payments_count"] == 2
    assert latest["customers_count"] == 2
    assert latest["sales_touched_count"] == 2
    assert Decimal(latest["total_collected"]) == Decimal("700.00")
    assert latest["total_customers_in_area"] == 2
    assert latest["customers_pending_in_area"] == 2
    assert len(latest["payments"]) == 2


@pytest.mark.asyncio
async def test_latest_customer_payment_activity_ignores_advance_payments_from_newer_sales(client):
    # A genuine CP collection visit must stay "the latest" activity even if a
    # brand-new sale (with an advance/full payment taken at sale time) gets
    # created afterward -- that advance is part of the sale, not a later
    # collection round, and must never hijack this activity just because its
    # CustomerPayment row happens to be the most recently created one.
    suffix = _unique()
    cp_area = f"GenuineCP-{suffix}"
    sale_area = f"NewerSale-{suffix}"
    product = await _create_product(client, f"FAN-ORD{suffix}")

    cp_customer = await _create_customer(client, f"Genuine CP Customer{suffix}", cp_area)
    sale = (
        await client.post(
            "/sales",
            json={
                "customer_id": cp_customer["id"],
                "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
            },
        )
    ).json()
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "600.00"})
    assert resp.status_code == 201

    # Now record a newer, unrelated sale with an advance payment in a different area.
    newer_customer = await _create_customer(client, f"Newer Sale Customer{suffix}", sale_area)
    resp = await client.post(
        "/sales",
        json={
            "customer_id": newer_customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "500.00", "quantity": 1}],
            "initial_payment": {"amount": "200.00"},
        },
    )
    assert resp.status_code == 201

    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    latest = resp.json()["latest_customer_payments"]
    assert latest is not None
    assert latest["area"] == cp_area
    assert latest["customers_count"] == 1
    assert Decimal(latest["total_collected"]) == Decimal("600.00")
    assert all(p["customer_id"] != newer_customer["id"] for p in latest["payments"])


@pytest.mark.asyncio
async def test_dashboard_handles_no_data_gracefully_when_only_other_areas_exist(client):
    # Sanity: even with prior data from other tests in the DB, the endpoint
    # must always resolve (never 500) and return well-formed nullable fields.
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "latest_sales" in data
    assert "latest_customer_payments" in data
