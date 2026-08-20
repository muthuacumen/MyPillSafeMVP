"""Public sidecar-status ticker (Task T2, GET /api/v1/status/sidecar).

No auth. Most tests here mock `brains_registry.is_sidecar_healthy()` directly
(one layer up from the httpx mocking in test_brains_registry.py) and only
exercise this route's own 20s cache. The staleness-bound test below instead
drives the REAL `is_sidecar_healthy()` -> brains_registry health-cache path,
because mocking `is_sidecar_healthy()` away (as the other tests do) cannot
catch a bug in how it interacts with brains_registry's own cache.
"""
import time as time_module

import httpx
import pytest
from httpx import AsyncClient

from app.api.v1.routes import status as status_route
from app.core.config import settings
from app.services import brains_registry


@pytest.fixture(autouse=True)
def _reset_status_cache():
    """The endpoint's cache is a module-level dict, process-global like
    brains_registry's -- reset between tests so one test's result can't
    leak into the next."""
    status_route._cached_payload = None
    status_route._cached_at = 0.0
    yield
    status_route._cached_payload = None
    status_route._cached_at = 0.0


@pytest.mark.asyncio
async def test_sidecar_up_reports_up_message(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _healthy():
        return True

    monkeypatch.setattr(brains_registry, "is_sidecar_healthy", _healthy)

    resp = await client.get("/api/v1/status/sidecar")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sidecar_up"] is True
    assert body["message"] == settings.SIDECAR_UP_MESSAGE
    assert "checked_at" in body


@pytest.mark.asyncio
async def test_sidecar_down_reports_down_message(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _unhealthy():
        return False

    monkeypatch.setattr(brains_registry, "is_sidecar_healthy", _unhealthy)

    resp = await client.get("/api/v1/status/sidecar")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sidecar_up"] is False
    assert body["message"] == settings.SIDECAR_DOWN_MESSAGE


@pytest.mark.asyncio
async def test_no_auth_required(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _unhealthy():
        return False

    monkeypatch.setattr(brains_registry, "is_sidecar_healthy", _unhealthy)
    resp = await client.get("/api/v1/status/sidecar")
    assert resp.status_code == 200  # no 401/403 -- no Authorization header sent


@pytest.mark.asyncio
async def test_result_is_cached_across_calls(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    call_count = 0

    async def _counting_check():
        nonlocal call_count
        call_count += 1
        return True

    monkeypatch.setattr(brains_registry, "is_sidecar_healthy", _counting_check)

    first = await client.get("/api/v1/status/sidecar")
    second = await client.get("/api/v1/status/sidecar")

    assert first.status_code == second.status_code == 200
    assert call_count == 1, "second call within the 20s cache window must not re-check the sidecar"


@pytest.mark.asyncio
async def test_cache_expires_and_rechecks(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    call_count = 0

    async def _counting_check():
        nonlocal call_count
        call_count += 1
        return True

    monkeypatch.setattr(brains_registry, "is_sidecar_healthy", _counting_check)

    await client.get("/api/v1/status/sidecar")
    # Force the cache to look expired without a real 20s sleep.
    status_route._cached_at -= 21.0
    await client.get("/api/v1/status/sidecar")

    assert call_count == 2


# --- real is_sidecar_healthy() <-> brains_registry cache interaction --------
#
# Regression: is_sidecar_healthy() used to read brains_registry's own 30s
# per-URL health cache, so this route's 20s cache sat ON TOP of that --
# a sidecar that died right after the 30s cache last refreshed could still
# report "up" for up to ~50s. The fix makes is_sidecar_healthy() force-
# refresh past that cache, so this route's own 20s cache is the ONLY
# staleness bound. Time is faked via time.monotonic (both brains_registry.py
# and status.py call it directly) so this proves the bound without sleeping.


@pytest.mark.asyncio
async def test_ticker_flips_within_20s_of_real_sidecar_death(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URLS", "")
    monkeypatch.setattr(settings, "BRAINS_SERVICE_URL", "http://sidecar-under-test:8100")
    brains_registry._health_cache.clear()
    brains_registry.set_pin(None)

    probe_up = {"value": True}

    class _ToggleAsyncClient:
        """Stands in for httpx.AsyncClient -- GET /health succeeds while
        probe_up["value"] is True, fails once flipped False, letting the
        test simulate the underlying sidecar dying mid-run."""

        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url, **kwargs):
            if probe_up["value"]:
                return httpx.Response(200, request=httpx.Request("GET", url))
            raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "AsyncClient", _ToggleAsyncClient)

    fake_now = {"t": 1_000_000.0}
    monkeypatch.setattr(time_module, "monotonic", lambda: fake_now["t"])

    try:
        # t=0: sidecar is up, ticker reports up and caches it.
        resp = await client.get("/api/v1/status/sidecar")
        assert resp.json()["sidecar_up"] is True

        # Sidecar dies. brains_registry's OWN 30s per-URL cache would still
        # say "healthy" for up to 30s more if is_sidecar_healthy() read it
        # normally -- this is exactly the staleness the fix removes.
        probe_up["value"] = False

        # +5s: still inside this route's 20s cache -- unchanged response is
        # correct here, this is the route's own (intended) cache window.
        fake_now["t"] += 5.0
        resp = await client.get("/api/v1/status/sidecar")
        assert resp.json()["sidecar_up"] is True

        # +21s total since the first call: past this route's 20s cache, but
        # still well within brains_registry's 30s cache. Before the fix,
        # is_sidecar_healthy() would return that stale cached "healthy"
        # reading and the ticker would incorrectly still say "up" (up to
        # ~50s total). After the fix, is_sidecar_healthy() force-refreshes
        # and the ticker flips within the 20s bound.
        fake_now["t"] += 16.0
        resp = await client.get("/api/v1/status/sidecar")
        assert resp.json()["sidecar_up"] is False, (
            "status route's 20s cache expired but the ticker still reported "
            "'up' -- is_sidecar_healthy() must force-refresh past "
            "brains_registry's 30s cache, not inherit its staleness"
        )
    finally:
        brains_registry._health_cache.clear()
        brains_registry.set_pin(None)
