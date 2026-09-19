"""
Coverage for the shop-profile onboarding endpoint and the customer/
manufacturer/shop image upload endpoints. Real uploads to Supabase Storage
aren't exercised here (no live bucket in CI/local test runs) -- `storage.
upload_image` is mocked so these tests verify the request/DB-update plumbing
around it, not the actual network call (that's `app/core/storage.py`'s job,
and it has no branching logic worth a unit test beyond what's covered by
manual verification against a real bucket).
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_shop_profile_update_sets_name_and_address(client):
    resp = await client.patch(
        "/shop-profile", json={"shop_name": "Sharma Traders", "shop_address": "MG Road", "shop_phone": "+91-9800000000"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["shop_name"] == "Sharma Traders"
    assert body["shop_address"] == "MG Road"
    assert body["shop_phone"] == "+91-9800000000"
    assert body["shop_logo_url"] is None
    assert body["shop_image_url"] is None


@pytest.mark.asyncio
async def test_shop_profile_update_is_partial(client):
    await client.patch("/shop-profile", json={"shop_name": "Sharma Traders"})
    resp = await client.patch("/shop-profile", json={"shop_address": "MG Road"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["shop_name"] == "Sharma Traders"  # untouched by the second call
    assert body["shop_address"] == "MG Road"


@pytest.mark.asyncio
async def test_shop_profile_rejects_blank_name(client):
    resp = await client.patch("/shop-profile", json={"shop_name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_auth_me_reflects_shop_profile(client):
    await client.patch("/shop-profile", json={"shop_name": "Sharma Traders"})
    resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["shop_name"] == "Sharma Traders"


@pytest.mark.asyncio
@patch("app.core.storage.upload_image", new_callable=AsyncMock)
async def test_shop_logo_upload_sets_shop_logo_url(mock_upload, client):
    mock_upload.return_value = "https://example.supabase.co/storage/v1/object/public/app-images/shop/x/logo.jpg"
    resp = await client.post("/shop-profile/logo", files={"file": ("logo.jpg", b"fake-bytes", "image/jpeg")})
    assert resp.status_code == 200
    assert resp.json()["shop_logo_url"] == mock_upload.return_value
    mock_upload.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.core.storage.upload_image", new_callable=AsyncMock)
async def test_customer_image_upload_sets_image_url(mock_upload, client):
    mock_upload.return_value = "https://example.supabase.co/storage/v1/object/public/app-images/customers/x/y.jpg"
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()

    resp = await client.post(f"/customers/{customer['id']}/image", files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")})
    assert resp.status_code == 200
    assert resp.json()["image_url"] == mock_upload.return_value

    resp = await client.get(f"/customers/{customer['id']}")
    assert resp.json()["image_url"] == mock_upload.return_value


@pytest.mark.asyncio
async def test_customer_image_upload_rejects_unsupported_type(client):
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()
    resp = await client.post(f"/customers/{customer['id']}/image", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("app.core.storage.upload_image", new_callable=AsyncMock)
async def test_manufacturer_image_upload_sets_image_url(mock_upload, client):
    mock_upload.return_value = "https://example.supabase.co/storage/v1/object/public/app-images/manufacturers/x/y.jpg"
    manufacturer = (await client.post("/manufacturers", json={"name": f"Manufacturer{_unique()}"})).json()

    resp = await client.post(
        f"/manufacturers/{manufacturer['id']}/image", files={"file": ("photo.png", b"fake-bytes", "image/png")}
    )
    assert resp.status_code == 200
    assert resp.json()["image_url"] == mock_upload.return_value


@pytest.mark.asyncio
@patch("app.core.storage.upload_image", new_callable=AsyncMock)
async def test_customer_image_can_be_cleared_via_patch(mock_upload, client):
    mock_upload.return_value = "https://example.supabase.co/storage/v1/object/public/app-images/customers/x/y.jpg"
    customer = (await client.post("/customers", json={"name": f"Customer{_unique()}"})).json()
    await client.post(f"/customers/{customer['id']}/image", files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")})

    resp = await client.patch(f"/customers/{customer['id']}", json={"image_url": None})
    assert resp.status_code == 200
    assert resp.json()["image_url"] is None
