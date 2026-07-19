import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scan_recorded_from_analyze_appears_unmatched(client: AsyncClient, auth_headers: dict):
    analyze_resp = await client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert analyze_resp.status_code == 200

    scans_resp = await client.get("/api/v1/scans/me", headers=auth_headers)
    assert scans_resp.status_code == 200
    records = scans_resp.json()
    assert len(records) == 1
    assert records[0]["drug_name"] == "Metformin HCl"
    # No active prescriptions on file yet -> can't be "matched"
    assert records[0]["match_status"] == "unmatched"


@pytest.mark.asyncio
async def test_scans_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/scans/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_blocked_from_scans(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/v1/scans/me", headers=admin_headers)
    assert response.status_code == 403
