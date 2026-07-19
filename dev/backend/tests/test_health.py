import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ci_test@pillsafe.dev",
            "password": "Test1234",
            "first_name": "CI",
            "last_name": "Test",
            "date_of_birth": "1990-01-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ci_login@pillsafe.dev",
            "password": "Test1234",
            "first_name": "CI",
            "last_name": "Login",
            "date_of_birth": "1990-01-01",
        },
    )
    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ci_login@pillsafe.dev", "password": "Test1234"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403
