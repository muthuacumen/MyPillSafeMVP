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
