import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """Shipped default: registration is admin-gated, so 202 and NO token.

    This asserted 201 + access_token until registration became approval-gated.
    The 201 + token path still exists and is still tested — under the
    kill-switch, in test_admin_approval.py.
    """
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
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending_approval"
    assert "access_token" not in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient, approve_user):
    # Register first — lands pending, so approve it the way an admin would
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
    await approve_user("ci_login@pillsafe.dev")
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
