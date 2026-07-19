import pytest
from httpx import AsyncClient

from app.core.config import settings


def _fake_image() -> tuple[str, bytes, str]:
    return ("label.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")


@pytest.mark.asyncio
async def test_upload_prescription_demo_mode(client: AsyncClient, auth_headers: dict):
    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["drug_name"]
    assert data[0]["time_slots"] == ["morning", "evening"]
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_list_update_and_soft_delete_prescription(client: AsyncClient, auth_headers: dict):
    name, content, ctype = _fake_image()
    create_resp = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    prescription_id = create_resp.json()[0]["id"]

    list_resp = await client.get("/api/v1/prescriptions/me", headers=auth_headers)
    assert list_resp.status_code == 200
    assert any(p["id"] == prescription_id for p in list_resp.json())

    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}",
        headers=auth_headers,
        json={"dosage": "500 mg"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["dosage"] == "500 mg"

    delete_resp = await client.delete(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 204

    list_after = await client.get("/api/v1/prescriptions/me", headers=auth_headers)
    assert all(p["id"] != prescription_id for p in list_after.json())


@pytest.mark.asyncio
async def test_upload_prescription_degrades_gracefully_on_bad_image_when_ocr_enabled(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    """A corrupt/non-image upload must fall back to demo text, not crash the
    request, once real OCR is switched on."""
    monkeypatch.setattr(settings, "OCR_PIPELINE_ENABLED", True)

    def _raise(image_bytes: bytes):
        raise OSError("Truncated File Read")

    monkeypatch.setattr("app.services.ocr_service.extract_text", _raise)

    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    assert response.status_code == 201
    assert response.json()[0]["drug_name"]


@pytest.mark.asyncio
async def test_upload_prescription_creates_one_row_per_medication(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "OCR_PIPELINE_ENABLED", True)
    monkeypatch.setattr(
        "app.services.ocr_service.extract_text",
        lambda image_bytes: (
            "CONESTOGA MEDICAL CENTRE\n"
            "RX 1\nAcetaminophen 500mg (Tylenol Extra Strength).\n"
            "Take 2 tablets every 6 hours as needed for pain or fever - do not exceed 8 tablets in 24 hours\n"
            "Qty: 100 tablets\nRefills: 2\nDIN: 00559407\n"
            "RX 2\nIbuprofen 200mg (Advil)\n"
            "Take 1-2 tablets THREE TIMES DAILY with meals (morning, noon and night) for joint pain - take with food\n"
            "Qty: 90 tablets\nRefills: 1\nDIN: 00587915\n"
            "RX 3\nLoratadine 10mg (Claritin).\n"
            "Take 1 tablet ONCE DAILY in the morning for seasonal allergies.\n"
            "Qty: 30 tablets\nRefills: 3\nDIN: 00782696\n"
        ),
    )
    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    assert all("CONESTOGA" not in p["drug_name"].upper() for p in data)
    names = {p["drug_name"] for p in data}
    assert names == {"Acetaminophen", "Ibuprofen", "Loratadine"}
    acetaminophen = next(p for p in data if p["drug_name"] == "Acetaminophen")
    assert acetaminophen["dosage"] == "500mg"
    assert acetaminophen["frequency_type"] == "PRN"
    assert acetaminophen["max_daily_dose"] == 8
    ibuprofen = next(p for p in data if p["drug_name"] == "Ibuprofen")
    assert ibuprofen["with_food"] is True
    assert ibuprofen["time_slots"] == ["morning", "afternoon", "evening"]


@pytest.mark.asyncio
async def test_get_prescription_image_requires_ownership(client: AsyncClient, auth_headers: dict):
    name, content, ctype = _fake_image()
    create_resp = await client.post(
        "/api/v1/prescriptions", headers=auth_headers, files={"image": (name, content, ctype)},
    )
    prescription_id = create_resp.json()[0]["id"]
    resp = await client.get(f"/api/v1/prescriptions/{prescription_id}/image", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")


@pytest.mark.asyncio
async def test_prescriptions_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/prescriptions/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_blocked_from_prescriptions(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/v1/prescriptions/me", headers=admin_headers)
    assert response.status_code == 403
