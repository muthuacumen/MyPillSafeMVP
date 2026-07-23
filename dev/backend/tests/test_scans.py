import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis


@pytest.mark.asyncio
async def test_scan_recorded_from_legacy_shaped_analysis_appears_unmatched(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """`GET /scans/me` must still correctly classify a legacy-shaped Analysis
    row (label_info-based, no SB2 `decision`/`detected`) as 'unmatched' when
    its drug isn't one of the patient's active prescriptions. The `/analyze`
    demo-stub that used to create rows like this via the API was removed
    (legacy cleanup) -- this test creates the row directly so scans.py's
    non-pill-v2 branch stays covered.
    """
    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user_id = me_resp.json()["id"]

    db_session.add(
        Analysis(
            user_id=user_id,
            status="completed",
            image_filename="pill.jpg",
            pills_detected=[],
            label_info={"drug_name": "Metformin HCl"},
            guidance="Take with food.",
            safety_alerts=[],
            ml_pipeline_enabled=False,
        )
    )
    await db_session.flush()

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
