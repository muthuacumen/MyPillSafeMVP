"""Sidecar pool: health-checked selection + admin pin override (Task A3).

Covers `app/services/brains_registry.py` directly (unit-level) and the two
`/admin/brains*` routes it backs. Mirrors the rest of the suite's
httpx-mocking idiom so these never talk to a real sidecar.
"""
import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import brains_registry


@pytest.fixture(autouse=True)
def _reset_registry_state():
    """Module-level health cache + pin are process-global -- reset between
    tests so one test's pin/health result can't leak into the next."""
    brains_registry._health_cache.clear()
    brains_registry.set_pin(None)
    yield
    brains_registry._health_cache.clear()
    brains_registry.set_pin(None)


class _AssertNeverCalledAsyncClient:
    """Instantiating this simulates a bug where a health check happened when
    it shouldn't have (back-compat: empty pool -> zero health-check calls)."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("httpx.AsyncClient must not be constructed when BRAINS_SERVICE_URLS is empty")


class _PerUrlHealthAsyncClient:
    """Stands in for httpx.AsyncClient -- GET {url}/health succeeds (200)
    for URLs in `healthy_urls`, raises a connection error for everything
    else. Lets a test declare "these URLs are up, these are down"."""

    healthy_urls: set[str] = set()

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, **kwargs):
        base = url.rsplit("/health", 1)[0]
        if base in _PerUrlHealthAsyncClient.healthy_urls:
            return httpx.Response(200, request=httpx.Request("GET", url))
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))


# --- resolve_brains_url() back-compat (A3.2 rule 1) --------------------------


@pytest.mark.asyncio
async def test_resolve_returns_single_url_with_no_health_check_when_pool_empty(
    monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "")
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URL", "http://127.0.0.1:8100")
    monkeypatch.setattr(httpx, "AsyncClient", _AssertNeverCalledAsyncClient)

    url = await brains_registry.resolve_brains_url()
    assert url == "http://127.0.0.1:8100"


# --- pool failover (A3.2 rule 2 + verification bar #7) -----------------------


@pytest.mark.asyncio
async def test_resolve_skips_dead_url_and_returns_live_one(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://dead:8100,http://live:8100")
    _PerUrlHealthAsyncClient.healthy_urls = {"http://live:8100"}
    monkeypatch.setattr(httpx, "AsyncClient", _PerUrlHealthAsyncClient)

    url = await brains_registry.resolve_brains_url()
    assert url == "http://live:8100"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_first_url_when_pool_entirely_dead(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://dead1:8100,http://dead2:8100")
    _PerUrlHealthAsyncClient.healthy_urls = set()
    monkeypatch.setattr(httpx, "AsyncClient", _PerUrlHealthAsyncClient)

    # Rule 2's last resort: name a concrete host even when nothing is
    # healthy, so downstream 503s still point somewhere real.
    url = await brains_registry.resolve_brains_url()
    assert url == "http://dead1:8100"


@pytest.mark.asyncio
async def test_pool_status_reports_health_for_every_configured_url(
    client: AsyncClient, admin_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://dead:8100,http://live:8100")
    _PerUrlHealthAsyncClient.healthy_urls = {"http://live:8100"}
    monkeypatch.setattr(httpx, "AsyncClient", _PerUrlHealthAsyncClient)

    resp = await client.get("/api/v1/admin/brains", headers=admin_headers)
    assert resp.status_code == 200
    rows = {r["url"]: r for r in resp.json()}
    assert rows["http://dead:8100"]["healthy"] is False
    assert rows["http://live:8100"]["healthy"] is True
    assert all("latency_ms" in r and "checked_at" in r for r in rows.values())


# --- pin behaviour -------------------------------------------------------------


@pytest.mark.asyncio
async def test_pin_prefers_pinned_url_when_healthy(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://a:8100,http://b:8100")
    _PerUrlHealthAsyncClient.healthy_urls = {"http://a:8100", "http://b:8100"}
    monkeypatch.setattr(httpx, "AsyncClient", _PerUrlHealthAsyncClient)

    brains_registry.set_pin("http://b:8100")
    url = await brains_registry.resolve_brains_url()
    assert url == "http://b:8100"


@pytest.mark.asyncio
async def test_pin_falls_through_to_healthy_pool_member_when_pinned_url_is_down(
    monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://a:8100,http://b:8100")
    _PerUrlHealthAsyncClient.healthy_urls = {"http://b:8100"}  # pinned "a" is down
    monkeypatch.setattr(httpx, "AsyncClient", _PerUrlHealthAsyncClient)

    brains_registry.set_pin("http://a:8100")
    url = await brains_registry.resolve_brains_url()
    assert url == "http://b:8100"


@pytest.mark.asyncio
async def test_admin_pin_rejects_url_outside_pool_with_422(
    client: AsyncClient, admin_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    """Verification bar #9 -- never accept an arbitrary URL (SSRF guard on
    an admin-authenticated endpoint)."""
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://a:8100,http://b:8100")

    resp = await client.post(
        "/api/v1/admin/brains/pin", headers=admin_headers, json={"url": "http://evil.example.com:9999"}
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"]["code"] == "INVALID_PIN_URL"
    assert brains_registry.get_pin() is None


@pytest.mark.asyncio
async def test_admin_pin_accepts_url_in_pool_and_unpins_with_null(
    client: AsyncClient, admin_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "http://a:8100,http://b:8100")

    resp = await client.post("/api/v1/admin/brains/pin", headers=admin_headers, json={"url": "http://b:8100"})
    assert resp.status_code == 200
    assert resp.json()["pinned"] == "http://b:8100"
    assert brains_registry.get_pin() == "http://b:8100"

    resp = await client.post("/api/v1/admin/brains/pin", headers=admin_headers, json={"url": None})
    assert resp.status_code == 200
    assert resp.json()["pinned"] is None
    assert brains_registry.get_pin() is None


@pytest.mark.asyncio
async def test_admin_brains_endpoints_require_admin_role(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/brains", headers=auth_headers)
    assert resp.status_code == 403

    resp = await client.post("/api/v1/admin/brains/pin", headers=auth_headers, json={"url": None})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_brains_endpoints_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/admin/brains")
    assert resp.status_code == 403
