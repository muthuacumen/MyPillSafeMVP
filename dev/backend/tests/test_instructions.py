import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_instruction_message_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/instructions/message",
        json={
            "drug_name": "Ibuprofen",
            "dosage": "200mg",
            "frequency_type": "TID",
            "specific_times": ["08:00", "13:00", "18:00"],
            "language": "en",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_instruction_message_tid_with_food_english(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/instructions/message",
        headers=auth_headers,
        json={
            "drug_name": "Ibuprofen",
            "dosage": "200mg",
            "frequency_type": "TID",
            "specific_times": ["08:00", "13:00", "18:00"],
            "with_food": True,
            "language": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "Ibuprofen" in data["message"]
    assert "8:00 AM" in data["message"]
    assert "6:00 PM" in data["message"]
    assert "food" in data["message"].lower()


@pytest.mark.asyncio
async def test_instruction_message_prn_includes_max_dose(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/instructions/message",
        headers=auth_headers,
        json={
            "drug_name": "Acetaminophen",
            "dosage": "500mg",
            "frequency_type": "PRN",
            "specific_times": [],
            "max_daily_dose": 8,
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert "8" in response.json()["message"]


@pytest.mark.asyncio
async def test_instruction_message_french(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/instructions/message",
        headers=auth_headers,
        json={
            "drug_name": "Loratadine",
            "dosage": "10mg",
            "frequency_type": "ONCE_DAILY",
            "specific_times": ["08:00"],
            "language": "fr",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "fr"
    assert "Prenez" in data["message"]


@pytest.mark.asyncio
async def test_instruction_message_unknown_language_falls_back_to_english(
    client: AsyncClient, auth_headers: dict
):
    response = await client.post(
        "/api/v1/instructions/message",
        headers=auth_headers,
        json={
            "drug_name": "Loratadine",
            "frequency_type": "ONCE_DAILY",
            "specific_times": ["08:00"],
            "language": "zz",
        },
    )
    assert response.status_code == 200
    assert response.json()["language"] == "en"
