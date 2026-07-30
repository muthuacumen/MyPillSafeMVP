"""GET /api/v1/reference/search -- the thin authenticated proxy the frontend
uses for the DIN "pick a different one" / edit-medication search box
(Phase 2). Never calls the sidecar from the browser; failure-tolerant like
the underlying brains_client.search_reference (down sidecar -> empty list,
not an error)."""
import httpx
import pytest
from httpx import AsyncClient


class _FakeGetResponse:
    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        return _FakeGetResponse(
            200,
            [{"din": "DIN13803", "product": "GRAVOL TABLETS", "strength": "50 MG", "score": 90.0}],
        )


class _UnreachableAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_reference_search_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/reference/search", params={"q": "gravol"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reference_search_proxies_and_converts_din(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    response = await client.get(
        "/api/v1/reference/search", headers=auth_headers, params={"q": "gravol"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["din"] == "00013803"  # canonical form, not the sidecar's "DIN13803"
    assert data[0]["product"] == "GRAVOL TABLETS"


@pytest.mark.asyncio
async def test_reference_search_sidecar_down_returns_empty_list_not_error(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    response = await client.get(
        "/api/v1/reference/search", headers=auth_headers, params={"q": "gravol"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_admin_blocked_from_reference_search(client: AsyncClient, admin_headers: dict):
    response = await client.get(
        "/api/v1/reference/search", headers=admin_headers, params={"q": "gravol"}
    )
    assert response.status_code == 403


# --- Task B2: the two-tier reference's pill_verifiable flag -------------------
# The sidecar now searches the 11,609-DIN profile tier and marks whether each
# hit is also in the 7,055-DIN appearance tier. The proxy must carry that
# through: it was being dropped here while the frontend type already declared
# it, so the field was silently always undefined.


class _TwoTierAsyncClient(_FakeAsyncClient):
    """Sidecar reply for a non-oral-solid (insulin) hit -- the Task B case."""

    async def get(self, url, **kwargs):
        return _FakeGetResponse(
            200,
            [
                {"din": "DIN2245689", "product": "LANTUS", "strength": None,
                 "score": 100.0, "pill_verifiable": False},
                {"din": "DIN13803", "product": "GRAVOL TABLETS", "strength": "50 MG",
                 "score": 90.0, "pill_verifiable": True},
            ],
        )


@pytest.mark.asyncio
async def test_reference_search_carries_pill_verifiable_both_ways(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(httpx, "AsyncClient", _TwoTierAsyncClient)
    response = await client.get(
        "/api/v1/reference/search", headers=auth_headers, params={"q": "lantus"}
    )
    assert response.status_code == 200
    data = response.json()
    assert [row["pill_verifiable"] for row in data] == [False, True]


@pytest.mark.asyncio
async def test_reference_search_missing_flag_is_unknown_not_false(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    """An older sidecar omits the field entirely. That must read as `None`
    (unknown), never `False` -- "we could not ask" must not render to the user
    as "this medication cannot be checked by photo"."""
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)  # reply has no flag
    response = await client.get(
        "/api/v1/reference/search", headers=auth_headers, params={"q": "gravol"}
    )
    assert response.status_code == 200
    assert response.json()[0]["pill_verifiable"] is None


# --- Query hygiene (2026-07-29 SA finding) ----------------------------------
#
# The sidecar matches with rapidfuzz WRatio and no score cutoff, so strength
# and dosage-form tokens in the query diluted the real drug token until
# generic words ("TABLET", "MG") scored ~85 against unrelated products.
# Measured live: "DIGOXIN 0.125 MG TABLET 0.125 mg" returned ALDACTONE /
# OVOL FOR GAS, and because `flag_not_in_reference` only fires on an EMPTY
# list, that junk reached the user with no warning.


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("DIGOXIN 0.125 MG TABLET", "DIGOXIN"),
        ("APO-ALENDRONATE 70 MG TABLET", "APO-ALENDRONATE"),
        ("ATORVASTATIN 20 MG", "ATORVASTATIN"),
        ("LANTUS 100 UNITS/ML", "LANTUS"),
        ("TEVA-NAPROXEN 500 MG TABLET", "TEVA-NAPROXEN"),
        ("AMOXICILLIN 500 MG Capsules", "AMOXICILLIN"),
        ("RAMIPRIL CAPSULE", "RAMIPRIL"),
        ("MOTRIN 400MG", "MOTRIN"),
        # No strength/form to strip -- must pass through untouched.
        ("Tylenol Extra Strength", "Tylenol Extra Strength"),
    ],
)
def test_clean_search_query_strips_strength_and_form(raw: str, expected: str):
    from app.services.brains_client import clean_search_query

    assert clean_search_query(raw) == expected


def test_clean_search_query_never_returns_empty():
    """A name that is ONLY a strength must fall back to the original text --
    stripping may never turn a searchable query into an unsearchable one."""
    from app.services.brains_client import clean_search_query

    assert clean_search_query("500 MG TABLET") == "500 MG TABLET"
    assert clean_search_query("   ") == ""


def test_rerank_by_strength_surfaces_the_labels_variant():
    """The sidecar returns exact-name matches all tied on score, so its order
    among them is arbitrary: searching "MOTRIN" put MOTRIN 200MG first and the
    label's MOTRIN 400MG fifth. The correct variant was always present, just
    not rank 1."""
    from app.services.brains_client import _rerank_by_strength

    rows = [
        {"din": "02186934", "product": "MOTRIN 200MG", "strength": "200 MG"},
        {"din": "02242632", "product": "MOTRIN 300MG", "strength": "300 MG"},
        {"din": "02242658", "product": "MOTRIN 400MG", "strength": "400 MG"},
    ]
    assert _rerank_by_strength(rows, "400 mg")[0]["product"] == "MOTRIN 400MG"
    # Ranking hint only -- an unmatched strength must not drop or reorder rows.
    assert _rerank_by_strength(rows, "999 mg") == rows
    assert _rerank_by_strength(rows, None) == rows


@pytest.mark.asyncio
async def test_search_reference_sends_the_cleaned_query(monkeypatch: pytest.MonkeyPatch):
    """Regression guard for the digoxin case: the strength must never reach
    the sidecar as a match token."""
    from app.services import brains_client

    sent: dict = {}

    class _CapturingClient(_FakeAsyncClient):
        async def get(self, url, **kwargs):
            sent.update(kwargs.get("params") or {})
            return _FakeGetResponse(200, [])

    monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)
    await brains_client.search_reference("DIGOXIN 0.125 MG TABLET", strength_hint="0.125 mg")
    assert sent["q"] == "DIGOXIN"
