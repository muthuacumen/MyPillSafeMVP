import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reminder_message_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/reminders/message",
        json={"medication_name": "Tylenol", "patient_first_name": "Sam", "language": "en"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reminder_message_default_english(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/reminders/message",
        headers=auth_headers,
        json={"medication_name": "Tylenol", "patient_first_name": "Sam"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert "Sam" in data["message"]
    assert "Tylenol" in data["message"]


@pytest.mark.asyncio
async def test_reminder_message_french(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/reminders/message",
        headers=auth_headers,
        json={"medication_name": "Tylenol", "patient_first_name": "Sam", "language": "fr-CA"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "fr"
    assert "Bonjour Sam" in data["message"]


@pytest.mark.asyncio
async def test_reminder_message_unknown_language_falls_back_to_english(
    client: AsyncClient, auth_headers: dict
):
    response = await client.post(
        "/api/v1/reminders/message",
        headers=auth_headers,
        json={"medication_name": "Tylenol", "patient_first_name": "Sam", "language": "zz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "zz"
    assert "Hi Sam" in data["message"]
