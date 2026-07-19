"""Phase 2 -- DIN linking at Rx-save: suggestion attach on prescription
create (sidecar mocked), sidecar-down graceful degradation, and the DIN
PATCH tri-state (confirm / reject-invalid / unset). Mirrors test_pill_v2.py's
httpx-mocking idiom so these tests never talk to a real sidecar."""
import httpx
import pytest
from httpx import AsyncClient


def _fake_image() -> tuple[str, bytes, str]:
    return ("label.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")


_CANNED_REFERENCE_RESULTS = [
    {"din": "DIN13803", "product": "GRAVOL TABLETS", "strength": "50 MG", "score": 90.0},
    {"din": "DIN2245867", "product": "GRAVOL LIQUID GELS", "strength": "50 MG", "score": 85.5},
]


class _FakeGetResponse:
    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self):
        return self._body


class _FakeAsyncClientWithResults:
    """Stands in for httpx.AsyncClient -- GET returns a canned reference-
    search reply, so the suggestion-attach path never hits a real sidecar."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        return _FakeGetResponse(200, _CANNED_REFERENCE_RESULTS)


class _UnreachableAsyncClient:
    """Stands in for httpx.AsyncClient -- every call raises, simulating the
    sidecar being down/unreachable."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))


# --- (a) suggestion attach on prescription create (sidecar mocked) ---------


@pytest.mark.asyncio
async def test_upload_prescription_attaches_din_suggestions(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClientWithResults)
    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    suggestions = data[0]["din_suggestions"]
    assert len(suggestions) == 2
    # DIN tokens converted to the app's canonical 8-digit zero-padded form,
    # never left in the sidecar's "DIN13803" token form.
    assert suggestions[0]["din"] == "00013803"
    assert suggestions[1]["din"] == "02245867"
    assert suggestions[0]["product"] == "GRAVOL TABLETS"
    assert suggestions[0]["score"] == 90.0
    # Never auto-committed.
    assert data[0]["din"] is None
    assert data[0]["din_confirmed"] is False


# --- (b) sidecar-down -> create still succeeds with empty suggestions ------


@pytest.mark.asyncio
async def test_upload_prescription_sidecar_down_still_creates_with_empty_suggestions(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    name, content, ctype = _fake_image()
    response = await client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        files={"image": (name, content, ctype)},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["din_suggestions"] == []
    assert data[0]["drug_name"]
    assert data[0]["din"] is None
    assert data[0]["din_confirmed"] is False


# --- (c) DIN PATCH: happy path, invalid rejection, unset -------------------


async def _create_one_prescription(client: AsyncClient, auth_headers: dict) -> str:
    name, content, ctype = _fake_image()
    create_resp = await client.post(
        "/api/v1/prescriptions", headers=auth_headers, files={"image": (name, content, ctype)}
    )
    return create_resp.json()[0]["id"]


@pytest.mark.asyncio
async def test_patch_din_happy_path_confirms(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)  # suggestion attach not under test here
    prescription_id = await _create_one_prescription(client, auth_headers)

    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": "13803"}
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["din"] == "00013803"
    assert body["din_confirmed"] is True


@pytest.mark.asyncio
async def test_patch_din_accepts_sb2_token_form(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    prescription_id = await _create_one_prescription(client, auth_headers)

    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": "DIN13803"}
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["din"] == "00013803"
    assert body["din_confirmed"] is True


@pytest.mark.asyncio
async def test_patch_din_invalid_rejected(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    prescription_id = await _create_one_prescription(client, auth_headers)

    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": "not-a-din"}
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["detail"]["error"]["code"] == "INVALID_DIN"

    # The invalid attempt must not have partially applied.
    list_resp = await client.get("/api/v1/prescriptions/me", headers=auth_headers)
    row = next(p for p in list_resp.json() if p["id"] == prescription_id)
    assert row["din"] is None
    assert row["din_confirmed"] is False


@pytest.mark.asyncio
async def test_patch_din_null_unsets(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    prescription_id = await _create_one_prescription(client, auth_headers)

    confirm_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": "00013803"}
    )
    assert confirm_resp.json()["din_confirmed"] is True

    clear_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": None}
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["din"] is None
    assert clear_resp.json()["din_confirmed"] is False


@pytest.mark.asyncio
async def test_patch_without_din_field_leaves_din_untouched(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    prescription_id = await _create_one_prescription(client, auth_headers)

    await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"din": "00013803"}
    )
    patch_resp = await client.patch(
        f"/api/v1/prescriptions/{prescription_id}", headers=auth_headers, json={"dosage": "500 mg"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["din"] == "00013803"
    assert patch_resp.json()["din_confirmed"] is True
