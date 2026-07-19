import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_contact_submission_no_auth_required(client: AsyncClient):
    response = await client.post(
        "/api/v1/contact",
        json={
            "full_name": "Jane Caregiver",
            "email": "jane@example.com",
            "message": "How do I add a second patient profile?",
        },
    )
    assert response.status_code == 201
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_contact_validates_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/contact",
        json={"full_name": "Jane", "email": "not-an-email", "message": "hi"},
    )
    assert response.status_code == 422
