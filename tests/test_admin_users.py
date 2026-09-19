"""
Coverage for the admin user-management surface: create, enable/disable,
expiry, and that a non-admin is locked out of it entirely.
"""
import uuid
from datetime import date, timedelta

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_admin_can_create_a_user(admin_client):
    email = f"newuser{_unique()}@example.com"
    resp = await admin_client.post(
        "/admin/users", json={"email": email, "password": "Password1!", "full_name": "New User"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "STAFF"
    assert body["is_active"] is True
    assert body["expires_at"] is None


@pytest.mark.asyncio
async def test_admin_cannot_create_duplicate_email(admin_client):
    email = f"dupe{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Password1!"})
    assert resp.status_code == 201
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "Password1!"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_admin_can_disable_and_re_enable_a_user(admin_client):
    resp = await admin_client.post(
        "/admin/users", json={"email": f"toggle{_unique()}@example.com", "password": "Password1!"}
    )
    user_id = resp.json()["id"]

    resp = await admin_client.patch(f"/admin/users/{user_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = await admin_client.patch(f"/admin/users/{user_id}", json={"is_active": True})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_admin_can_set_and_clear_expiry(admin_client):
    resp = await admin_client.post(
        "/admin/users", json={"email": f"expiry{_unique()}@example.com", "password": "Password1!"}
    )
    user_id = resp.json()["id"]

    future = (date.today() + timedelta(days=30)).isoformat()
    resp = await admin_client.patch(f"/admin/users/{user_id}", json={"expires_at": future})
    assert resp.status_code == 200
    assert resp.json()["expires_at"] == future

    resp = await admin_client.patch(f"/admin/users/{user_id}", json={"expires_at": None})
    assert resp.status_code == 200
    assert resp.json()["expires_at"] is None


@pytest.mark.asyncio
async def test_admin_can_list_and_get_users(admin_client):
    resp = await admin_client.post(
        "/admin/users", json={"email": f"list{_unique()}@example.com", "password": "Password1!"}
    )
    user_id = resp.json()["id"]

    resp = await admin_client.get("/admin/users")
    assert resp.status_code == 200
    assert any(u["id"] == user_id for u in resp.json())

    resp = await admin_client.get(f"/admin/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id
    assert "features" in resp.json()


@pytest.mark.asyncio
async def test_admin_can_reset_a_users_password(client, admin_client):
    email = f"resetpw{_unique()}@example.com"
    resp = await admin_client.post("/admin/users", json={"email": email, "password": "OldPassword1!"})
    user_id = resp.json()["id"]

    resp = await admin_client.patch(f"/admin/users/{user_id}", json={"password": "NewPassword2!"})
    assert resp.status_code == 200
    # Reset must not leak the password back, and shouldn't disturb any other field.
    assert "password" not in resp.json()
    assert resp.json()["email"] == email

    resp = await client.post("/auth/login", json={"email": email, "password": "OldPassword1!"})
    assert resp.status_code == 401

    resp = await client.post("/auth/login", json={"email": email, "password": "NewPassword2!"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_non_admin_is_forbidden_from_admin_routes(client):
    resp = await client.get("/admin/users")
    assert resp.status_code == 403

    resp = await client.post("/admin/users", json={"email": "x@example.com", "password": "Password1!"})
    assert resp.status_code == 403
