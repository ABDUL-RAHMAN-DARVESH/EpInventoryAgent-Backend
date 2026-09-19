"""
End-to-end HTTP flow tests matching the acceptance criteria in the project spec:
customer sale + payments, manufacturer purchase + payments, and dashboard totals.
"""
import uuid
from decimal import Decimal

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


async def _create_customer(client, name="ABC Traders"):
    resp = await client.post("/customers", json={"name": name, "area": "Downtown"})
    assert resp.status_code == 201
    return resp.json()


async def _create_manufacturer(client, name="XYZ Electronics"):
    resp = await client.post("/manufacturers", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


async def _create_product(client, sku, name="Samsung TV"):
    resp = await client.post("/products", json={"sku": sku, "name": name, "brand": "Samsung"})
    assert resp.status_code == 201
    return resp.json()


async def _run_customer_flow(client, suffix=""):
    customer = await _create_customer(client, f"ABC Traders E2E{_unique(suffix)}")
    product = await _create_product(client, f"TV-001-E2E{_unique(suffix)}")

    # 1. Create sale for 1,00,000 (2 x 50,000)
    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "50000.00", "quantity": 2}],
        },
    )
    assert resp.status_code == 201
    sale = resp.json()
    assert Decimal(sale["total_amount"]) == Decimal("100000.00")
    assert Decimal(sale["balance_due"]) == Decimal("100000.00")
    assert sale["payment_status"] == "PENDING"

    # 2. Record 20,000 advance
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "20000.00"})
    assert resp.status_code == 201

    # 3. Verify outstanding balance = 80,000
    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("80000.00")
    assert sale["payment_status"] == "PARTIALLY_PAID"

    # 4. Record 10,000 payment
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "10000.00"})
    assert resp.status_code == 201

    # 5. Verify outstanding balance = 70,000
    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("70000.00")

    # 6. Record another payment
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "70000.00"})
    assert resp.status_code == 201
    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("0.00")
    assert sale["payment_status"] == "PAID"

    # 7. Verify payment history
    resp = await client.get(f"/sales/{sale['id']}/payments")
    payments = resp.json()
    assert len(payments) == 3
    assert sum(Decimal(p["amount"]) for p in payments) == Decimal("100000.00")

    # 8. Overpayment must be rejected
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "1.00"})
    assert resp.status_code == 422

    return customer, sale


@pytest.mark.asyncio
async def test_customer_sale_and_payment_flow(client):
    await _run_customer_flow(client)


async def _run_manufacturer_flow(client, suffix=""):
    manufacturer = await _create_manufacturer(client, f"XYZ Electronics E2E{_unique(suffix)}")
    product = await _create_product(client, f"TV-001-MFG-E2E{_unique(suffix)}")

    # 1. Create purchase for 1,00,000 (10 units)
    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 10, "line_total": "100000.00"}],
        },
    )
    assert resp.status_code == 201
    purchase = resp.json()
    assert Decimal(purchase["total_amount"]) == Decimal("100000.00")

    # 2. Record 55,000 payment
    resp = await client.post(f"/purchases/{purchase['id']}/payments", json={"amount": "55000.00"})
    assert resp.status_code == 201

    # 3. Verify outstanding payable = 45,000
    resp = await client.get(f"/purchases/{purchase['id']}")
    purchase = resp.json()
    assert Decimal(purchase["balance_due"]) == Decimal("45000.00")
    assert purchase["payment_status"] == "PARTIALLY_PAID"

    # 4. Record another payment
    resp = await client.post(f"/purchases/{purchase['id']}/payments", json={"amount": "45000.00"})
    assert resp.status_code == 201

    # 5. Verify payment history
    resp = await client.get(f"/purchases/{purchase['id']}/payments")
    payments = resp.json()
    assert len(payments) == 2
    assert sum(Decimal(p["amount"]) for p in payments) == Decimal("100000.00")

    resp = await client.get(f"/purchases/{purchase['id']}")
    purchase = resp.json()
    assert Decimal(purchase["balance_due"]) == Decimal("0.00")
    assert purchase["payment_status"] == "PAID"

    return manufacturer, purchase


@pytest.mark.asyncio
async def test_manufacturer_purchase_and_payment_flow(client):
    await _run_manufacturer_flow(client)


@pytest.mark.asyncio
async def test_dashboard_reflects_transactions(client):
    before = (await client.get("/dashboard")).json()

    await _run_customer_flow(client, suffix="-dash")
    await _run_manufacturer_flow(client, suffix="-dash")

    after = (await client.get("/dashboard")).json()

    # Both flows end fully paid, so receivables/payables delta should be zero,
    # but collected/paid totals must have increased by the full sale/purchase amounts.
    assert Decimal(after["total_collected_from_customers"]) - Decimal(
        before["total_collected_from_customers"]
    ) == Decimal("100000.00")
    assert Decimal(after["total_paid_to_manufacturers"]) - Decimal(
        before["total_paid_to_manufacturers"]
    ) == Decimal("100000.00")
    assert Decimal(after["total_receivables"]) == Decimal(before["total_receivables"])
    assert Decimal(after["total_payables"]) == Decimal(before["total_payables"])
