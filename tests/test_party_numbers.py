import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User, UserRole
from app.repositories import user as user_repo


async def _another_owner_client():
    email = f"other-{uuid.uuid4().hex}@example.com"
    async with AsyncSessionLocal() as session:
        await user_repo.create(
            session,
            User(email=email, hashed_password=hash_password("Test1234!"), full_name="Other", role=UserRole.STAFF),
        )
        await session.commit()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1")
    response = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


@pytest.mark.asyncio
async def test_customer_numbers_are_unique_and_sequential(client):
    suffix = uuid.uuid4().hex[:8]
    first = await client.post("/customers", json={"name": f"Duplicate {suffix}"})
    second = await client.post("/customers", json={"name": f"Duplicate {suffix}"})

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    first_body, second_body = first.json(), second.json()
    assert first_body["name"] == second_body["name"]
    assert first_body["id"] != second_body["id"]
    assert second_body["customer_number"] == first_body["customer_number"] + 1

    other = await _another_owner_client()
    try:
        other_response = await other.post("/customers", json={"name": f"Duplicate {suffix}"})
        assert other_response.status_code == 201, other_response.text
        assert other_response.json()["customer_number"] == 1
    finally:
        await other.aclose()


@pytest.mark.asyncio
async def test_manufacturer_numbers_are_unique_and_sequential(client):
    suffix = uuid.uuid4().hex[:8]
    first = await client.post("/manufacturers", json={"name": f"Duplicate {suffix}"})
    second = await client.post("/manufacturers", json={"name": f"Duplicate {suffix}"})

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    first_body, second_body = first.json(), second.json()
    assert first_body["name"] == second_body["name"]
    assert first_body["id"] != second_body["id"]
    assert second_body["manufacturer_number"] == first_body["manufacturer_number"] + 1

    other = await _another_owner_client()
    try:
        other_response = await other.post("/manufacturers", json={"name": f"Duplicate {suffix}"})
        assert other_response.status_code == 201, other_response.text
        assert other_response.json()["manufacturer_number"] == 1
    finally:
        await other.aclose()
