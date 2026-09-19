"""
Coverage for the feature catalog + per-user toggles: nothing is hard-coded --
a feature only exists once an admin creates it, and is off for a user until
explicitly turned on for them.
"""
import uuid

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


async def _create_staff_user(admin_client):
    email = f"staff{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_admin_can_create_a_feature(admin_client):
    key = f"barcode_scanner_{uuid.uuid4().hex[:6]}"
    resp = await admin_client.post("/admin/features", json={"key": key, "name": "Barcode Scanner"})
    assert resp.status_code == 201
    assert resp.json()["key"] == key


@pytest.mark.asyncio
async def test_feature_is_off_by_default_for_a_new_user(admin_client):
    key = f"reports_{uuid.uuid4().hex[:6]}"
    await admin_client.post("/admin/features", json={"key": key, "name": "Advanced Reports"})
    user = await _create_staff_user(admin_client)

    resp = await admin_client.get(f"/admin/users/{user['id']}")
    features = {f["key"]: f["enabled"] for f in resp.json()["features"]}
    assert features[key] is False


@pytest.mark.asyncio
async def test_toggling_a_feature_is_reflected_on_auth_me(client, admin_client):
    key = f"barcode_{uuid.uuid4().hex[:6]}"
    await admin_client.post("/admin/features", json={"key": key, "name": "Barcode"})

    me = (await client.get("/auth/me")).json()
    user_id = me["id"]
    assert {f["key"]: f["enabled"] for f in me["features"]}[key] is False

    resp = await admin_client.patch(f"/admin/users/{user_id}/features/{key}", json={"enabled": True})
    assert resp.status_code == 200

    me = (await client.get("/auth/me")).json()
    assert {f["key"]: f["enabled"] for f in me["features"]}[key] is True

    resp = await admin_client.patch(f"/admin/users/{user_id}/features/{key}", json={"enabled": False})
    assert resp.status_code == 200
    me = (await client.get("/auth/me")).json()
    assert {f["key"]: f["enabled"] for f in me["features"]}[key] is False


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_features(client):
    resp = await client.post("/admin/features", json={"key": "x", "name": "X"})
    assert resp.status_code == 403
