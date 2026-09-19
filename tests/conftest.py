import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User, UserRole
from app.repositories import user as user_repo

TEST_USER_PASSWORD = "Test1234!"


@pytest.fixture
async def client():
    """A fresh, real (non-admin) user is created per test function and the
    shared client is pre-authenticated as them -- every existing test keeps
    working unmodified, just running as one authenticated user instead of
    anonymously. As a side effect, each test's data is isolated from every
    other test's (and from the real bootstrap admin/demo accounts), since
    they're now different owners -- no more test data leaking into anyone's
    real dashboard."""
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            hashed_password=hash_password(TEST_USER_PASSWORD),
            full_name="Test User",
            role=UserRole.STAFF,
        )
        await user_repo.create(session, user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        resp = await ac.post("/auth/login", json={"email": email, "password": TEST_USER_PASSWORD})
        assert resp.status_code == 200, resp.text
        ac.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
        yield ac


@pytest.fixture
async def admin_client():
    """Same idea as `client`, but the fresh user is an ADMIN -- for exercising
    the /admin/* endpoints."""
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            hashed_password=hash_password(TEST_USER_PASSWORD),
            full_name="Test Admin",
            role=UserRole.ADMIN,
        )
        await user_repo.create(session, user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        resp = await ac.post("/auth/login", json={"email": email, "password": TEST_USER_PASSWORD})
        assert resp.status_code == 200, resp.text
        ac.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
        yield ac
