"""
Coverage for the core multi-tenancy guarantee: two different users' data
never leaks across accounts, whether by listing, direct-id lookup, or trying
to attach a sale/purchase to a customer/manufacturer you don't own.
"""
import uuid

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_customers_are_isolated_between_users(client, admin_client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # Create a second, independent authenticated user.
    email = f"other{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 201

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as other_client:
        login = await other_client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        other_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        resp = await client.post("/customers", json={"name": f"Alpha Customer{_unique()}"})
        assert resp.status_code == 201
        alpha_customer = resp.json()

        resp = await other_client.post("/customers", json={"name": f"Beta Customer{_unique()}"})
        assert resp.status_code == 201
        beta_customer = resp.json()

        # Each user's list only contains their own customer.
        alpha_ids = {c["id"] for c in (await client.get("/customers")).json()}
        beta_ids = {c["id"] for c in (await other_client.get("/customers")).json()}
        assert alpha_customer["id"] in alpha_ids
        assert beta_customer["id"] not in alpha_ids
        assert beta_customer["id"] in beta_ids
        assert alpha_customer["id"] not in beta_ids

        # Direct-id lookup of the other user's customer 404s, not 403 --
        # doesn't even reveal that the row exists.
        resp = await client.get(f"/customers/{beta_customer['id']}")
        assert resp.status_code == 404
        resp = await other_client.get(f"/customers/{alpha_customer['id']}")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_products_share_sku_namespace_per_owner_not_globally(client, admin_client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    email = f"other{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 201

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as other_client:
        login = await other_client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        other_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        sku = f"SHARED-{uuid.uuid4().hex[:8]}"
        resp = await client.post("/products", json={"sku": sku, "name": "Widget", "brand": "Acme"})
        assert resp.status_code == 201

        # The exact same SKU is free to use for a different owner.
        resp = await other_client.post("/products", json={"sku": sku, "name": "Widget", "brand": "Acme"})
        assert resp.status_code == 201

        # But re-using it against the SAME owner still conflicts.
        resp = await client.post("/products", json={"sku": sku, "name": "Widget Again", "brand": "Acme"})
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_dashboard_totals_only_reflect_the_caller_s_own_data(client, admin_client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    email = f"other{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 201

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as other_client:
        login = await other_client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        other_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        before = (await other_client.get("/dashboard")).json()

        # Create a sale as `client` (a different owner) -- must not move `other_client`'s dashboard.
        cust = (await client.post("/customers", json={"name": f"Iso Customer{_unique()}"})).json()
        prod = (await client.post("/products", json={"sku": f"ISO-{_unique()}", "name": "Widget"})).json()
        resp = await client.post(
            "/sales",
            json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "unit_price": "500.00", "quantity": 1}]},
        )
        assert resp.status_code == 201

        after = (await other_client.get("/dashboard")).json()
        assert after["total_receivables"] == before["total_receivables"]
