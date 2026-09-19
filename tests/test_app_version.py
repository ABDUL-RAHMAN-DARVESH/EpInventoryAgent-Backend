"""
Coverage for admin-configurable app version policy + the public /version/check
endpoint the app uses to decide "update available" vs. "force update".
"""
import uuid

import pytest


@pytest.mark.asyncio
async def test_admin_can_set_and_read_app_version(admin_client):
    platform = f"android-{uuid.uuid4().hex[:6]}"
    resp = await admin_client.put(f"/admin/app-versions/{platform}", json={"latest_version": "2.3.0", "minimum_version": "2.0.0"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["platform"] == platform
    assert body["latest_version"] == "2.3.0"
    assert body["minimum_version"] == "2.0.0"

    resp = await admin_client.get("/admin/app-versions")
    assert resp.status_code == 200
    assert any(v["platform"] == platform for v in resp.json())


@pytest.mark.asyncio
async def test_version_check_is_public_and_requires_no_auth(client, admin_client):
    platform = f"android-{uuid.uuid4().hex[:6]}"
    await admin_client.put(f"/admin/app-versions/{platform}", json={"latest_version": "2.3.0", "minimum_version": "2.0.0"})

    del client.headers["Authorization"]
    resp = await client.get("/version/check", params={"platform": platform, "version": "2.3.0"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_version_below_minimum_forces_update(client, admin_client):
    platform = f"android-{uuid.uuid4().hex[:6]}"
    await admin_client.put(f"/admin/app-versions/{platform}", json={"latest_version": "2.3.0", "minimum_version": "2.0.0"})

    resp = await client.get("/version/check", params={"platform": platform, "version": "1.5.0"})
    body = resp.json()
    assert body["force_update"] is True
    assert body["update_available"] is True


@pytest.mark.asyncio
async def test_version_below_latest_but_above_minimum_is_available_not_forced(client, admin_client):
    platform = f"android-{uuid.uuid4().hex[:6]}"
    await admin_client.put(f"/admin/app-versions/{platform}", json={"latest_version": "2.3.0", "minimum_version": "2.0.0"})

    resp = await client.get("/version/check", params={"platform": platform, "version": "2.1.0"})
    body = resp.json()
    assert body["force_update"] is False
    assert body["update_available"] is True


@pytest.mark.asyncio
async def test_version_at_latest_needs_no_update(client, admin_client):
    platform = f"android-{uuid.uuid4().hex[:6]}"
    await admin_client.put(f"/admin/app-versions/{platform}", json={"latest_version": "2.3.0", "minimum_version": "2.0.0"})

    resp = await client.get("/version/check", params={"platform": platform, "version": "2.3.0"})
    body = resp.json()
    assert body["force_update"] is False
    assert body["update_available"] is False


@pytest.mark.asyncio
async def test_unconfigured_platform_never_blocks(client):
    platform = f"unconfigured-{uuid.uuid4().hex[:6]}"
    resp = await client.get("/version/check", params={"platform": platform, "version": "0.0.1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["force_update"] is False
    assert body["update_available"] is False


@pytest.mark.asyncio
async def test_non_admin_cannot_set_app_version(client):
    resp = await client.put("/admin/app-versions/android", json={"latest_version": "9.9.9", "minimum_version": "9.9.9"})
    assert resp.status_code == 403
