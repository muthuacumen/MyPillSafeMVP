"""/analyze/pill/v2 -- the ONLY pill-scan endpoint as of Phase 3 (the legacy
OpenCV path was removed entirely). Mirrors the other route tests' httpx-
mocking idiom so these never talk to a real sidecar in CI."""
import json

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import brains_client

_CANNED_NO_MATCH_RESPONSE = {
    "record": {
        "detected": True,
        "photo": "pill.jpg",
        "colour_modes": [{"top2": [["orange", 0.72], ["peach", 0.21]]}],
        "shape_out": "round",
        "shape_conf": 0.91,
        "type_out": "tablet",
        "type_conf": 0.5,
        "imprint_reads": {"i1": "APO 200", "i3": "APO 200"},
        "bbox": [10, 10, 50, 50],
        "det_conf": 0.94,
        "shadow_fusion_suspected": False,
        "colour_calib_method": "C-A",
    },
    "match": None,
    "note": "no profile DINs supplied — matching skipped",
}


def _canned_response(decision: str, *, abstain_action: str | None = None, matched_din_token: str | None = None):
    """A sidecar /pill/analyze reply with a real SB2 `match` block, shaped
    exactly like `sb2.matcher.match_profile`'s output (CONTRACT.md §4)."""
    breakdown = {
        "S": 0.91, "colour_score": 1.0, "shape_score": 1.0, "type_score": 1.0,
        "imprint_exact": True, "imprint_fuzzy": 1.0, "ask_to_flip": False,
    }
    ranked_candidates = [
        ["DIN13803", 0.91, breakdown],
        ["DIN2245867", 0.34, {**breakdown, "S": 0.34, "imprint_exact": False}],
    ]
    return {
        "record": {
            "detected": True,
            "photo": "pill.jpg",
            "colour_modes": [{"top2": [["orange", 0.72], ["peach", 0.21]]}],
            "shape_out": "round",
            "shape_conf": 0.91,
            "type_out": "tablet",
            "type_conf": 0.5,
            "imprint_reads": {"i1": "APO 200", "i3": "APO 200"},
            "bbox": [10, 10, 50, 50],
            "det_conf": 0.94,
            "shadow_fusion_suspected": True,
            "colour_calib_method": "C-A",
        },
        "match": {
            "decision": decision,
            "matched_din": matched_din_token,
            "ranked_candidates": ranked_candidates,
            "abstain_action": abstain_action,
            "disclaimer": "Decision-support only -- not a clinical determination. Verify with a pharmacist.",
        },
    }


_CANNED_NOT_DETECTED_RESPONSE = {
    "record": {"detected": False, "photo": "pill.jpg", "error": None},
    "match": None,
}

_CANNED_REFERENCE_CANDIDATES = {
    "DIN13803": {"din": "DIN13803", "product": "GRAVOL TABLETS", "ai": "DIMENHYDRINATE", "strength": "50 MG"},
    "DIN2245867": {"din": "DIN2245867", "product": "GRAVOL LIQUID GELS", "ai": "DIMENHYDRINATE", "strength": "50 MG"},
}


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient so tests never hit a real sidecar.
    Used for the main POST /pill/analyze call; class-level `response_body`
    lets each test pick which canned reply to serve."""

    response_body: dict = _CANNED_NO_MATCH_RESPONSE
    last_kwargs: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        _FakeAsyncClient.last_kwargs = {"url": url, **kwargs}
        return _FakeResponse(200, _FakeAsyncClient.response_body)


class _UnreachableAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    async def get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))


class _AssertNeverCalledAsyncClient:
    """Instantiating this simulates a bug where the sidecar got called when
    it shouldn't have (empty-profile short-circuit)."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("httpx.AsyncClient must not be constructed when profile_dins is empty")


async def _fake_get_reference_candidates(dins: list[str]) -> dict[str, dict]:
    return {d: _CANNED_REFERENCE_CANDIDATES[d] for d in dins if d in _CANNED_REFERENCE_CANDIDATES}


async def _create_confirmed_prescription(client: AsyncClient, auth_headers: dict, din: str, monkeypatch) -> str:
    """Create a prescription and confirm it with `din` (canonical or SB2
    token form). Suggestion-attach on create runs against whatever sidecar
    double is currently monkeypatched -- callers should set up an
    unreachable double first so create-time suggestion attach degrades
    harmlessly, matching Phase 2's contract."""
    resp = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": ("rx.jpg", b"fake-bytes", "image/jpeg")},
    )
    prescription_id = resp.json()[0]["id"]
    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": din}
    )
    assert patch_resp.json()["din_confirmed"] is True
    return prescription_id


# --- flag / auth -------------------------------------------------------------


@pytest.mark.asyncio
async def test_pill_v2_disabled_returns_501(client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", False)
    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 501
    assert response.json()["detail"]["error"]["code"] == "PILL_V2_DISABLED"


def test_pill_v2_enabled_by_default():
    """Phase 3: PILL_V2_ENABLED is now a pure kill-switch, default ON --
    `/analyze/pill/v2` is the only pill endpoint that exists."""
    assert settings.model_fields["PILL_V2_ENABLED"].default is True


@pytest.mark.asyncio
async def test_pill_v2_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/analyze/pill/v2",
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_legacy_pill_endpoint_removed(client: AsyncClient, auth_headers: dict):
    """The pre-v2 OpenCV pill-analyze endpoint no longer exists at all. POST
    /analyze/pill now falls through to analyze.py's generic GET-only
    `/{analysis_id}` route (path matches, method doesn't) -- 405, not 404 --
    which itself confirms no POST handler for this path exists anymore."""
    response = await client.post(
        "/api/v1/analyze/pill",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 405


# --- empty-profile short-circuit ---------------------------------------------


@pytest.mark.asyncio
async def test_pill_v2_empty_profile_short_circuits_without_calling_sidecar(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    # If the route tries to construct httpx.AsyncClient at all, this raises.
    monkeypatch.setattr(httpx, "AsyncClient", _AssertNeverCalledAsyncClient)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_profile"
    assert body["record"] is None
    assert body["match"] is None
    assert "medication" in body["message"].lower()


@pytest.mark.asyncio
async def test_pill_v2_unconfirmed_prescription_still_counts_as_empty_profile(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)  # suggestion-attach at create time
    await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": ("rx.jpg", b"fake-bytes", "image/jpeg")},
    )  # created but never confirmed with a DIN

    monkeypatch.setattr(httpx, "AsyncClient", _AssertNeverCalledAsyncClient)
    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "no_profile"


# --- sidecar unreachable ------------------------------------------------------


@pytest.mark.asyncio
async def test_pill_v2_sidecar_unreachable_returns_503(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "BRAINS_UNAVAILABLE"


# --- profile DIN filtering (Phase 2 behaviour, re-verified under Phase 3 route) ---


@pytest.mark.asyncio
async def test_pill_v2_profile_dins_only_confirmed_active_in_sb2_token_form(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)

    async def _create(image_name: str) -> str:
        resp = await client.post(
            "/api/v1/prescriptions",
            headers=auth_headers,
            files={"image": (image_name, b"fake-bytes", "image/jpeg")},
        )
        return resp.json()[0]["id"]

    confirmed_active_id = await _create("rx1.jpg")
    await _create("rx2.jpg")  # left unconfirmed -- must not appear
    confirmed_inactive_id = await _create("rx3.jpg")

    await client.patch(f"/api/v1/prescriptions/{confirmed_active_id}", headers=auth_headers, json={"din": "13803"})
    await client.patch(
        f"/api/v1/prescriptions/{confirmed_inactive_id}", headers=auth_headers, json={"din": "2245867"}
    )
    await client.delete(f"/api/v1/prescriptions/{confirmed_inactive_id}", headers=auth_headers)

    _FakeAsyncClient.response_body = _CANNED_NO_MATCH_RESPONSE
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    sent_dins = json.loads(_FakeAsyncClient.last_kwargs["data"]["profile_dins"])
    assert sent_dins == ["DIN13803"]


# --- decision states: verify / reject / abstain -- each persists a scan row --


@pytest.mark.asyncio
async def test_pill_v2_verify_response_shape_and_scan_row(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    _FakeAsyncClient.response_body = _canned_response("verify", matched_din_token="DIN13803")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(brains_client, "get_reference_candidates", _fake_get_reference_candidates)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["record"]["detected"] is True
    match = body["match"]
    assert match["decision"] == "verify"
    assert match["matched_din"] == "00013803"  # SB2 token converted to canonical
    assert match["abstain_action"] is None
    assert match["disclaimer"]
    top = match["ranked_candidates"][0]
    assert top["din"] == "00013803"
    assert top["product"] == "GRAVOL TABLETS"
    assert top["strength"] == "50 MG"
    assert top["breakdown"]["imprint_exact"] is True

    scans_resp = await client.get("/api/v1/scans/me", headers=auth_headers)
    rows = scans_resp.json()
    assert len(rows) == 1
    assert rows[0]["decision"] == "verify"
    assert rows[0]["matched_din"] == "00013803"
    assert rows[0]["match_status"] == "matched"
    assert rows[0]["detected"] is True
    assert rows[0]["top_candidate_score"] == 0.91
    assert rows[0]["shadow_fusion_suspected"] is True


@pytest.mark.asyncio
async def test_pill_v2_reject_response_shape_and_scan_row(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    _FakeAsyncClient.response_body = _canned_response("reject")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(brains_client, "get_reference_candidates", _fake_get_reference_candidates)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    match = response.json()["match"]
    assert match["decision"] == "reject"
    assert match["matched_din"] is None
    assert match["abstain_action"] is None

    scans_resp = await client.get("/api/v1/scans/me", headers=auth_headers)
    rows = scans_resp.json()
    assert rows[0]["decision"] == "reject"
    assert rows[0]["matched_din"] is None
    assert rows[0]["match_status"] == "unmatched"


@pytest.mark.asyncio
async def test_pill_v2_abstain_ask_to_flip_response_shape_and_scan_row(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    _FakeAsyncClient.response_body = _canned_response("abstain", abstain_action="ask_to_flip")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(brains_client, "get_reference_candidates", _fake_get_reference_candidates)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    match = response.json()["match"]
    assert match["decision"] == "abstain"
    assert match["abstain_action"] == "ask_to_flip"
    # Abstain must NEVER collapse into reject.
    assert match["decision"] != "reject"

    scans_resp = await client.get("/api/v1/scans/me", headers=auth_headers)
    rows = scans_resp.json()
    assert rows[0]["decision"] == "abstain"
    assert rows[0]["abstain_action"] == "ask_to_flip"
    # abstain maps to "warning" (amber), never "unmatched" (red).
    assert rows[0]["match_status"] == "warning"


@pytest.mark.asyncio
async def test_pill_v2_abstain_shortlist_response_shape(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    _FakeAsyncClient.response_body = _canned_response("abstain", abstain_action="shortlist")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(brains_client, "get_reference_candidates", _fake_get_reference_candidates)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    match = response.json()["match"]
    assert match["decision"] == "abstain"
    assert match["abstain_action"] == "shortlist"
    assert len(match["ranked_candidates"]) == 2
    assert {c["product"] for c in match["ranked_candidates"]} == {"GRAVOL TABLETS", "GRAVOL LIQUID GELS"}


@pytest.mark.asyncio
async def test_pill_v2_not_detected_scan_row(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "PILL_V2_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    await _create_confirmed_prescription(client, auth_headers, "13803", monkeypatch)

    _FakeAsyncClient.response_body = _CANNED_NOT_DETECTED_RESPONSE
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    response = await client.post(
        "/api/v1/analyze/pill/v2",
        headers=auth_headers,
        files={"image": ("pill.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["detected"] is False
    assert body["match"] is None

    scans_resp = await client.get("/api/v1/scans/me", headers=auth_headers)
    rows = scans_resp.json()
    assert rows[0]["detected"] is False
    assert rows[0]["decision"] is None
