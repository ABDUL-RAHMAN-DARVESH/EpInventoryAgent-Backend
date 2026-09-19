"""
Coverage for products: SKU is no longer part of the model at all (just name,
brand, category), deleting a product is a real hard delete that's blocked
when the product has sales/purchase history, and purchased/sold/available
quantity is derived live from purchase/sale line items.
"""
import uuid

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_product_can_be_created_with_just_a_name(client):
    resp = await client.post("/products", json={"name": f"Table Fan{_unique()}"})
    assert resp.status_code == 201
    body = resp.json()
    assert "sku" not in body
    assert body["brand"] is None
    assert body["category"] is None
    assert body["total_purchased"] == 0
    assert body["total_sold"] == 0
    assert body["available_quantity"] == 0


@pytest.mark.asyncio
async def test_quantity_tracking_reflects_purchases_and_sales(client):
    product = (await client.post("/products", json={"name": f"Tracked Widget{_unique()}"})).json()
    manufacturer = (await client.post("/manufacturers", json={"name": f"Manufacturer{_unique()}"})).json()
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()

    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 10, "line_total": "1000.00"}],
        },
    )
    assert resp.status_code == 201

    resp = await client.get(f"/products/{product['id']}")
    body = resp.json()
    assert body["total_purchased"] == 10
    assert body["total_sold"] == 0
    assert body["available_quantity"] == 10

    resp = await client.post(
        "/sales",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "unit_price": "50.00", "quantity": 4}]},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/products/{product['id']}")
    body = resp.json()
    assert body["total_purchased"] == 10
    assert body["total_sold"] == 4
    assert body["available_quantity"] == 6

    # A second purchase and a second sale both accumulate correctly.
    await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 5, "line_total": "500.00"}],
        },
    )
    resp = await client.post(
        "/sales",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "unit_price": "50.00", "quantity": 6}]},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/products/{product['id']}")
    body = resp.json()
    assert body["total_purchased"] == 15
    assert body["total_sold"] == 10
    assert body["available_quantity"] == 5


@pytest.mark.asyncio
async def test_quantity_can_reach_zero_when_fully_sold(client):
    product = (await client.post("/products", json={"name": f"Cleared Widget{_unique()}"})).json()
    manufacturer = (await client.post("/manufacturers", json={"name": f"Manufacturer{_unique()}"})).json()
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()

    await client.post(
        "/purchases",
        json={"manufacturer_id": manufacturer["id"], "items": [{"product_id": product["id"], "quantity": 3, "line_total": "300.00"}]},
    )
    resp = await client.post(
        "/sales",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "unit_price": "100.00", "quantity": 3}]},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/products/{product['id']}")
    assert resp.json()["available_quantity"] == 0


@pytest.mark.asyncio
async def test_product_list_includes_quantity_stats_for_every_product(client):
    manufacturer = (await client.post("/manufacturers", json={"name": f"Manufacturer{_unique()}"})).json()
    product_a = (await client.post("/products", json={"name": f"Widget A{_unique()}"})).json()
    product_b = (await client.post("/products", json={"name": f"Widget B{_unique()}"})).json()
    await client.post(
        "/purchases",
        json={"manufacturer_id": manufacturer["id"], "items": [{"product_id": product_a["id"], "quantity": 7, "line_total": "70.00"}]},
    )

    resp = await client.get("/products", params={"limit": 500})
    assert resp.status_code == 200
    by_id = {p["id"]: p for p in resp.json()}
    assert by_id[product_a["id"]]["available_quantity"] == 7
    assert by_id[product_b["id"]]["available_quantity"] == 0


@pytest.mark.asyncio
async def test_unused_product_can_be_deleted(client):
    product = (await client.post("/products", json={"name": f"Unused Widget{_unique()}"})).json()

    resp = await client.delete(f"/products/{product['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/products/{product['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_product_with_sale_history_cannot_be_deleted(client):
    product = (await client.post("/products", json={"name": f"Sold Widget{_unique()}"})).json()
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()
    resp = await client.post(
        "/sales",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "unit_price": "100.00", "quantity": 1}]},
    )
    assert resp.status_code == 201

    resp = await client.delete(f"/products/{product['id']}")
    assert resp.status_code == 409

    # Still there afterward.
    resp = await client.get(f"/products/{product['id']}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_product_with_purchase_history_cannot_be_deleted(client):
    product = (await client.post("/products", json={"name": f"Purchased Widget{_unique()}"})).json()
    manufacturer = (await client.post("/manufacturers", json={"name": f"Manufacturer{_unique()}"})).json()
    resp = await client.post(
        "/purchases",
        json={
            "manufacturer_id": manufacturer["id"],
            "items": [{"product_id": product["id"], "quantity": 1, "line_total": "100.00"}],
        },
    )
    assert resp.status_code == 201

    resp = await client.delete(f"/products/{product['id']}")
    assert resp.status_code == 409
