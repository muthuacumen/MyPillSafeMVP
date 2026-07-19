import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/v1/patients/me/password",
        headers=auth_headers,
        json={"current_password": "WrongPass1", "new_password": "NewPass123"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_change_password_and_login_with_new_password(client: AsyncClient):
    email = f"pw_{uuid.uuid4().hex[:10]}@pillsafe.dev"
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Test1234",
            "first_name": "Pw",
            "last_name": "Test",
            "date_of_birth": "1990-01-01",
        },
    )
    token = register_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    change_resp = await client.patch(
        "/api/v1/patients/me/password",
        headers=headers,
        json={"current_password": "Test1234", "new_password": "NewPass123"},
    )
    assert change_resp.status_code == 204

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "NewPass123"}
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_my_account(client: AsyncClient, auth_headers: dict):
    delete_resp = await client.delete("/api/v1/patients/me", headers=auth_headers)
    assert delete_resp.status_code == 204

    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_blocked_from_password_change(client: AsyncClient, admin_headers: dict):
    response = await client.patch(
        "/api/v1/patients/me/password",
        headers=admin_headers,
        json={"current_password": "Admin1234", "new_password": "NewPass123"},
    )
    assert response.status_code == 403
