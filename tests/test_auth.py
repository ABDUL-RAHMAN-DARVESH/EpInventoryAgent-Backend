"""
Coverage for login, token refresh, and the account-usability checks
(disabled / expired) that get3_current_user re-verifies on every request.
"""
import uuid
from datetime import date, timedelta

import pytest


def _unique(suffix: str = "") -> str:
    return f"{suffix}-{uuid.uuid4().hex[:8]}"


async def _create_user(admin_client, *, password="Test1234!", is_active=True, expires_at=None, role="STAFF"):
    email = f"user{_unique()}@example.com"
    resp = await admin_client.post(
        "/admin/users",
        json={"email": email, "password": password, "role": role, "expires_at": expires_at},
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    if not is_active:
        resp = await admin_client.patch(f"/admin/users/{user['id']}", json={"is_active": False})
        assert resp.status_code == 200
    return email, user


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_credentials(client, admin_client):
    email, _user = await _create_user(admin_client)
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(client, admin_client):
    email, _user = await _create_user(admin_client)
    resp = await client.post("/auth/login", json={"email": email, "password": "WrongPassword1!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_fails_for_unknown_email(client):
    resp = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_a_token(client):
    # `client` carries its own bearer token; strip it to simulate an anonymous caller.
    del client.headers["Authorization"]
    resp = await client.get("/customers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_disabled_user_cannot_log_in(client, admin_client):
    email, _user = await _create_user(admin_client, is_active=False)
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_user_cannot_log_in(client, admin_client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    email, _user = await _create_user(admin_client, expires_at=yesterday)
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_disabling_a_user_immediately_breaks_their_existing_token(client, admin_client):
    # The whole point of re-checking is_active on every request (not just at
    # login) -- a token issued while active must stop working the moment
    # an admin disables the account, without waiting for it to expire.
    email, user = await _create_user(admin_client)
    login_resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    token = login_resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/customers")
    assert resp.status_code == 200  # still active

    disable_resp = await admin_client.patch(f"/admin/users/{user['id']}", json={"is_active": False})
    assert disable_resp.status_code == 200

    resp = await client.get("/customers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_issues_a_working_new_access_token(client, admin_client):
    email, _user = await _create_user(admin_client)
    login_resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_access_token = refresh_resp.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {new_access_token}"
    resp = await client.get("/customers")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_me_returns_profile_and_feature_flags(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"]
    assert body["is_active"] is True
    assert isinstance(body["features"], list)
