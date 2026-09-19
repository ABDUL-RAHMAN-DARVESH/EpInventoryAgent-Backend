"""
Coverage for editing previously recorded data: sale/purchase due_date & notes,
and customer/manufacturer payment amount/date/method/reference/notes -- making
sure balance_due/amount_paid/payment_status stay correct after an edit.
"""
import uuid
from decimal import Decimal

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


async def _create_customer(client, name):
    resp = await client.post("/customers", json={"name": name, "area": "Downtown"})
    assert resp.status_code == 201
    return resp.json()


async def _create_manufacturer(client, name):
    resp = await client.post("/manufacturers", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


async def _create_product(client, sku, name="Samsung TV"):
    resp = await client.post("/products", json={"sku": sku, "name": name, "brand": "Samsung"})
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_update_sale_due_date_and_notes(client):
    customer = await _create_customer(client, f"Edit Sale Co{_unique()}")
    product = await _create_product(client, f"TV-EDIT{_unique()}")

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
        },
    )
    sale = resp.json()

    resp = await client.patch(f"/sales/{sale['id']}", json={"due_date": "2030-01-01", "notes": "Updated notes"})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["due_date"] == "2030-01-01"
    assert updated["notes"] == "Updated notes"
    # Editing due_date/notes must not touch money fields.
    assert Decimal(updated["total_amount"]) == Decimal(sale["total_amount"])
    assert Decimal(updated["balance_due"]) == Decimal(sale["balance_due"])


@pytest.mark.asyncio
async def test_update_purchase_due_date_and_notes(client):
    manufacturer = await _create_manufacturer(client, f"Edit Purchase Co{_unique()}")
    product = await _create_product(client, f"TV-EDIT-MFG{_unique()}")

    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 1, "line_total": "1000.00"}],
        },
    )
    purchase = resp.json()

    resp = await client.patch(f"/purchases/{purchase['id']}", json={"due_date": "2030-01-01", "notes": "Updated"})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["due_date"] == "2030-01-01"
    assert updated["notes"] == "Updated"


@pytest.mark.asyncio
async def test_update_customer_payment_amount_recalculates_sale(client):
    customer = await _create_customer(client, f"Edit Payment Co{_unique()}")
    product = await _create_product(client, f"TV-EDIT-PAY{_unique()}")

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
        },
    )
    sale = resp.json()

    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "400.00"})
    assert resp.status_code == 201
    payment = resp.json()

    resp = await client.get(f"/sales/{sale['id']}")
    assert Decimal(resp.json()["balance_due"]) == Decimal("600.00")
    assert resp.json()["payment_status"] == "PARTIALLY_PAID"

    # Raise the payment amount -- balance_due should shrink to match.
    resp = await client.patch(f"/sales/{sale['id']}/payments/{payment['id']}", json={"amount": "1000.00"})
    assert resp.status_code == 200
    assert Decimal(resp.json()["amount"]) == Decimal("1000.00")

    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("0.00")
    assert Decimal(sale["amount_paid"]) == Decimal("1000.00")
    assert sale["payment_status"] == "PAID"

    # Editing amount, method, reference, and notes together must all persist.
    resp = await client.patch(
        f"/sales/{sale['id']}/payments/{payment['id']}",
        json={"amount": "250.00", "method": "UPI", "reference_number": "REF-42", "notes": "corrected"},
    )
    assert resp.status_code == 200
    edited = resp.json()
    assert Decimal(edited["amount"]) == Decimal("250.00")
    assert edited["method"] == "UPI"
    assert edited["reference_number"] == "REF-42"
    assert edited["notes"] == "corrected"

    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("750.00")
    assert sale["payment_status"] == "PARTIALLY_PAID"

    # Pushing the amount past the sale total must be rejected, leaving data untouched.
    resp = await client.patch(f"/sales/{sale['id']}/payments/{payment['id']}", json={"amount": "5000.00"})
    assert resp.status_code == 422
    resp = await client.get(f"/sales/{sale['id']}")
    assert Decimal(resp.json()["balance_due"]) == Decimal("750.00")


@pytest.mark.asyncio
async def test_update_sale_items_recalculates_total(client):
    customer = await _create_customer(client, f"Edit Items Co{_unique()}")
    product_a = await _create_product(client, f"TV-ITEMS-A{_unique()}")
    product_b = await _create_product(client, f"TV-ITEMS-B{_unique()}")

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product_a["id"], "unit_price": "100.00", "quantity": 2}],
        },
    )
    sale = resp.json()
    assert Decimal(sale["total_amount"]) == Decimal("200.00")

    # Replace items entirely with a larger set -- total_amount should follow.
    resp = await client.patch(
        f"/sales/{sale['id']}",
        json={
            "items": [
                {"product_id": product_a["id"], "unit_price": "100.00", "quantity": 1},
                {"product_id": product_b["id"], "unit_price": "50.00", "quantity": 3},
            ]
        },
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert Decimal(updated["total_amount"]) == Decimal("250.00")
    assert Decimal(updated["balance_due"]) == Decimal("250.00")
    assert len(updated["items"]) == 2

    # Pay most of it, then try to shrink the total below what's already paid.
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "200.00"})
    assert resp.status_code == 201

    resp = await client.patch(
        f"/sales/{sale['id']}",
        json={"items": [{"product_id": product_a["id"], "unit_price": "10.00", "quantity": 1}]},
    )
    assert resp.status_code == 422

    resp = await client.get(f"/sales/{sale['id']}")
    assert Decimal(resp.json()["total_amount"]) == Decimal("250.00")


@pytest.mark.asyncio
async def test_delete_sale_payment_recalculates_balance(client):
    customer = await _create_customer(client, f"Delete Payment Co{_unique()}")
    product = await _create_product(client, f"TV-DEL-PAY{_unique()}")

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "1000.00", "quantity": 1}],
        },
    )
    sale = resp.json()

    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "400.00"})
    payment = resp.json()

    resp = await client.delete(f"/sales/{sale['id']}/payments/{payment['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/sales/{sale['id']}")
    sale = resp.json()
    assert Decimal(sale["balance_due"]) == Decimal("1000.00")
    assert Decimal(sale["amount_paid"]) == Decimal("0.00")
    assert sale["payment_status"] == "PENDING"

    resp = await client.get(f"/sales/{sale['id']}/payments")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_sale_removes_it_and_its_payments(client):
    customer = await _create_customer(client, f"Delete Sale Co{_unique()}")
    product = await _create_product(client, f"TV-DEL-SALE{_unique()}")

    resp = await client.post(
        "/sales",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "unit_price": "500.00", "quantity": 1}],
        },
    )
    sale = resp.json()
    resp = await client.post(f"/sales/{sale['id']}/payments", json={"amount": "200.00"})
    assert resp.status_code == 201

    resp = await client.delete(f"/sales/{sale['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/sales/{sale['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_purchase_removes_it_and_its_payments(client):
    manufacturer = await _create_manufacturer(client, f"Delete Purchase Mfg{_unique()}")
    product = await _create_product(client, f"TV-DEL-PURCHASE{_unique()}")

    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 1, "line_total": "500.00"}],
        },
    )
    purchase = resp.json()
    resp = await client.post(f"/purchases/{purchase['id']}/payments", json={"amount": "200.00"})
    assert resp.status_code == 201

    resp = await client.delete(f"/purchases/{purchase['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/purchases/{purchase['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_manufacturer_payment_amount_recalculates_purchase(client):
    manufacturer = await _create_manufacturer(client, f"Edit Payment Mfg{_unique()}")
    product = await _create_product(client, f"TV-EDIT-PAY-MFG{_unique()}")

    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 1, "line_total": "1000.00"}],
        },
    )
    purchase = resp.json()

    resp = await client.post(f"/purchases/{purchase['id']}/payments", json={"amount": "300.00"})
    assert resp.status_code == 201
    payment = resp.json()

    resp = await client.patch(f"/purchases/{purchase['id']}/payments/{payment['id']}", json={"amount": "800.00"})
    assert resp.status_code == 200

    resp = await client.get(f"/purchases/{purchase['id']}")
    purchase = resp.json()
    assert Decimal(purchase["balance_due"]) == Decimal("200.00")
    assert Decimal(purchase["amount_paid"]) == Decimal("800.00")
    assert purchase["payment_status"] == "PARTIALLY_PAID"
