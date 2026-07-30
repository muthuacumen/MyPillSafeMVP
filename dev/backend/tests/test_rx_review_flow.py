"""FixbyOPUS3 Task A3/A5 -- the review workflow end to end at the route
layer: proposals land pending, the qwen proposer is used when the sidecar
answers, the regex proposer takes over when it does not, blocking flags gate
approval, and schedule-bearing surfaces only ever see approved medications.
"""
import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import brains_client, ocr_service, rx_extract_service


def _fake_image() -> tuple[str, bytes, str]:
    return ("label.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")


_WEEKLY_LABEL = (
    "Rexall Pharmacy\n"
    "APO-ALENDRONATE 70 MG TABLET\n"
    "TAKE 1 TABLET ONCE WEEKLY ON AN EMPTY STOMACH WITH A FULL GLASS OF WATER\n"
    "Qty: 4  Refills: 2\n"
)

_DAILY_LABEL = (
    "Shoppers Drug Mart #1123\n"
    "APO-AMLODIPINE 5 MG TABLET\n"
    "TAKE 1 TABLET BY MOUTH ONCE DAILY\n"
    "Qty: 90  Refills: 3\n"
)


@pytest.fixture
def real_ocr(monkeypatch: pytest.MonkeyPatch):
    """Turn the OCR pipeline on and let each test supply the label text."""
    monkeypatch.setattr(settings, "OCR_PIPELINE_ENABLED", True)

    def _use(raw_text: str):
        async def _extract(image_bytes, filename, content_type):
            return raw_text
        monkeypatch.setattr(ocr_service, "extract_text", _extract)

    return _use


@pytest.fixture
def llm_proposer(monkeypatch: pytest.MonkeyPatch):
    """Stand in for the sidecar's /rx/extract (conftest disables the LLM
    proposer by default for hermeticity -- these tests opt back in)."""
    monkeypatch.setattr(settings, "RX_LLM_PARSE_ENABLED", True)

    def _returns(medications: list[dict]):
        async def _extract(raw_text: str) -> dict:
            return {"medications": medications, "model": "qwen2.5:7b-instruct", "elapsed_seconds": 1.0}
        monkeypatch.setattr(rx_extract_service, "extract_medications", _extract)

    def _down():
        async def _extract(raw_text: str) -> dict:
            raise rx_extract_service.RxExtractUnavailableError("sidecar unreachable")
        monkeypatch.setattr(rx_extract_service, "extract_medications", _extract)

    _returns.down = _down  # type: ignore[attr-defined]
    return _returns


async def _upload(client: AsyncClient, auth_headers: dict) -> list[dict]:
    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions", headers=auth_headers, files={"image": (name, content, ctype)}
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- proposals land pending -------------------------------------------------

@pytest.mark.asyncio
async def test_scanned_medications_are_pending_and_attributed_to_qwen(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_DAILY_LABEL)
    llm_proposer([{
        "drug_name": "APO-AMLODIPINE 5 MG TABLET", "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)
    assert med["review_status"] == "pending"
    assert med["parse_source"] == "qwen"
    assert med["specific_times"] == ["08:00"]
    assert med["drug_name"] == "APO-AMLODIPINE 5 MG TABLET"
    # The LLM proposer has no notion of day-part slots; the guardrails
    # recompute them from the derived times so an LLM-parsed medication
    # renders with the same badges as a regex-parsed one.
    assert med["time_slots"] == ["morning"]


@pytest.mark.asyncio
async def test_sidecar_down_falls_back_to_regex_with_honest_attribution(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    """Honest degradation: the scan still works, and the response says which
    proposer actually spoke rather than pretending it was the LLM."""
    real_ocr(_DAILY_LABEL)
    llm_proposer.down()
    [med] = await _upload(client, auth_headers)
    assert med["parse_source"] == "regex"
    assert med["review_status"] == "pending"
    assert med["specific_times"] == ["08:00"]


@pytest.mark.asyncio
async def test_weekly_medication_is_persisted_with_no_times_and_needs_schedule(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    """The catastrophic case: a once-weekly bisphosphonate must never be
    saved carrying a daily reminder time. Measured as a real regex-parser
    safety event on 2026-07-28."""
    real_ocr(_WEEKLY_LABEL)
    llm_proposer([{
        "drug_name": "APO-ALENDRONATE 70 MG TABLET", "dosage": "70 mg",
        "frequency_type": "WEEKLY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)
    assert med["specific_times"] == []
    assert "needs_schedule" in med["parse_flags"]


# --- the approval gate ------------------------------------------------------

@pytest.mark.asyncio
async def test_approving_a_needs_schedule_medication_requires_a_schedule(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_WEEKLY_LABEL)
    llm_proposer([{
        "drug_name": "APO-ALENDRONATE 70 MG TABLET", "dosage": "70 mg",
        "frequency_type": "WEEKLY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)

    blocked = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "approved"},
    )
    assert blocked.status_code == 422
    error = blocked.json()["detail"]["error"]
    assert error["code"] == "REVIEW_INCOMPLETE"
    assert error["unresolved_flags"] == ["needs_schedule"]

    approved = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "approved", "specific_times": ["09:00"], "time_slots": ["morning"]},
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["specific_times"] == ["09:00"]


@pytest.mark.asyncio
async def test_approving_a_not_on_label_medication_requires_confirming_that_field(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_DAILY_LABEL)
    llm_proposer([{
        # A strength that is nowhere on the label -- kept (never nulled) but
        # flagged, and the flag blocks approval until the user touches it.
        "drug_name": "APO-AMLODIPINE 5 MG TABLET", "dosage": "10 mg",
        "frequency_type": "ONCE_DAILY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)
    assert med["dosage"] == "10 mg", "G2 keeps the value; it does not null it"
    assert "not_on_label" in med["parse_flags"]

    blocked = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "approved", "dosage": "5 mg"},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["error"]["unresolved_flags"] == ["not_on_label"]

    approved = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "approved", "dosage": "5 mg", "confirmed_flags": ["not_on_label"]},
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["dosage"] == "5 mg"


@pytest.mark.asyncio
async def test_editing_a_pending_medication_never_silently_approves_it(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_DAILY_LABEL)
    llm_proposer([{
        "drug_name": "APO-AMLODIPINE 5 MG TABLET", "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)
    patched = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"drug_name": "Amlodipine", "dosage": "5 mg"},
    )
    assert patched.status_code == 200
    assert patched.json()["review_status"] == "pending"


@pytest.mark.asyncio
async def test_invalid_review_status_is_rejected(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_DAILY_LABEL)
    llm_proposer([{
        "drug_name": "APO-AMLODIPINE 5 MG TABLET", "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)
    response = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "yolo"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "INVALID_REVIEW_STATUS"


# --- schedule surfaces see approved medications only ------------------------

@pytest.mark.asyncio
async def test_schedule_surface_excludes_pending_medications(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    """`review_status=approved` is what the dashboard schedule and the dose
    -reminder engine ask for. A proposal the user has not approved must not
    be able to fire a reminder (non-negotiable §0.1)."""
    real_ocr(_DAILY_LABEL)
    llm_proposer([{
        "drug_name": "APO-AMLODIPINE 5 MG TABLET", "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY", "explicit_times": [], "with_food": False,
    }])
    [med] = await _upload(client, auth_headers)

    everything = await client.get("/api/v1/prescriptions/me", headers=auth_headers)
    assert any(p["id"] == med["id"] for p in everything.json()), "review screen needs it"

    schedule = await client.get(
        "/api/v1/prescriptions/me", headers=auth_headers, params={"review_status": "approved"}
    )
    assert all(p["id"] != med["id"] for p in schedule.json())

    await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers,
        json={"review_status": "approved"},
    )
    schedule_after = await client.get(
        "/api/v1/prescriptions/me", headers=auth_headers, params={"review_status": "approved"}
    )
    assert any(p["id"] == med["id"] for p in schedule_after.json())


@pytest.mark.asyncio
async def test_review_status_query_param_rejects_junk(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/v1/prescriptions/me", headers=auth_headers, params={"review_status": "approved-ish"}
    )
    assert response.status_code == 422


# --- kill-switch ------------------------------------------------------------

@pytest.mark.asyncio
async def test_rx_llm_parse_disabled_uses_regex_but_keeps_the_guardrails(
    client: AsyncClient, auth_headers: dict, real_ocr, monkeypatch: pytest.MonkeyPatch
):
    """`RX_LLM_PARSE_ENABLED=false` switches the PROPOSER off, never the
    safety layer -- a weekly label still gets zero reminder times."""
    monkeypatch.setattr(settings, "RX_LLM_PARSE_ENABLED", False)

    async def _must_not_be_called(raw_text: str) -> dict:
        raise AssertionError("the LLM proposer must not run when the flag is off")

    monkeypatch.setattr(rx_extract_service, "extract_medications", _must_not_be_called)
    real_ocr(_WEEKLY_LABEL)
    [med] = await _upload(client, auth_headers)
    assert med["parse_source"] == "regex"
    assert med["specific_times"] == []
    assert "needs_schedule" in med["parse_flags"]


@pytest.mark.asyncio
async def test_sidecar_returning_no_medications_falls_through_to_regex(
    client: AsyncClient, auth_headers: dict, real_ocr, llm_proposer
):
    real_ocr(_DAILY_LABEL)
    llm_proposer([])
    [med] = await _upload(client, auth_headers)
    assert med["parse_source"] == "regex"
    assert med["drug_name"]


# --- Task B3: is this medication checkable by photo at all? -----------------

@pytest.mark.asyncio
async def test_confirming_a_non_pill_verifiable_din_records_it_as_false(
    client: AsyncClient, auth_headers: dict, real_ocr, monkeypatch: pytest.MonkeyPatch
):
    """An insulin pen is a real, marketed, DIN-linkable medication that a
    photo cannot check. Before Task B it could not be DIN-linked at all;
    now it links and is labelled honestly."""
    real_ocr(_DAILY_LABEL)

    async def _profile(dins: list[str]):
        return {dins[0]: {"din": dins[0], "brand": "LANTUS", "pill_verifiable": False}}

    monkeypatch.setattr(brains_client, "get_profile_rows", _profile)
    [med] = await _upload(client, auth_headers)
    response = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers, json={"din": "02245689"},
    )
    assert response.status_code == 200
    assert response.json()["din_confirmed"] is True
    assert response.json()["pill_verifiable"] is False


@pytest.mark.asyncio
async def test_a_down_sidecar_leaves_pill_verifiable_unknown_not_false(
    client: AsyncClient, auth_headers: dict, real_ocr, monkeypatch: pytest.MonkeyPatch
):
    """The asymmetry that matters: "we could not ask" must not render as
    "this can't be checked by photo". A wrong such badge would teach a user
    not to bother verifying a pill they actually could have verified."""
    real_ocr(_DAILY_LABEL)

    async def _down(dins: list[str]):
        return None

    monkeypatch.setattr(brains_client, "get_profile_rows", _down)
    [med] = await _upload(client, auth_headers)
    response = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers, json={"din": "02245689"},
    )
    assert response.status_code == 200
    assert response.json()["din_confirmed"] is True
    assert response.json()["pill_verifiable"] is None


@pytest.mark.asyncio
async def test_clearing_the_din_clears_pill_verifiable(
    client: AsyncClient, auth_headers: dict, real_ocr, monkeypatch: pytest.MonkeyPatch
):
    real_ocr(_DAILY_LABEL)

    async def _profile(dins: list[str]):
        return {dins[0]: {"din": dins[0], "pill_verifiable": True}}

    monkeypatch.setattr(brains_client, "get_profile_rows", _profile)
    [med] = await _upload(client, auth_headers)
    await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers, json={"din": "02245689"},
    )
    cleared = await client.patch(
        f"/api/v1/prescriptions/{med['id']}", headers=auth_headers, json={"din": None},
    )
    assert cleared.json()["din_confirmed"] is False
    assert cleared.json()["pill_verifiable"] is None


# --- the raw httpx path (no service-level mock) -----------------------------

class _UnreachableAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

    async def post(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))


@pytest.mark.asyncio
async def test_real_rx_extract_client_degrades_to_regex_when_sidecar_unreachable(
    client: AsyncClient, auth_headers: dict, real_ocr, monkeypatch: pytest.MonkeyPatch
):
    """Exercises `rx_extract_service.extract_medications` itself (not
    mocked) against a simulated-unreachable transport -- the honest-
    degradation bar, at the HTTP layer rather than the service layer."""
    monkeypatch.setattr(settings, "RX_LLM_PARSE_ENABLED", True)
    real_ocr(_DAILY_LABEL)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    [med] = await _upload(client, auth_headers)
    assert med["parse_source"] == "regex"
    assert med["review_status"] == "pending"
