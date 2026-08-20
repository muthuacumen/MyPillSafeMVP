"""Admin sidecar-supervisor proxy (Task T2, app/api/v1/routes/admin_sidecar.py).

Mocks `httpx.AsyncClient` the same way test_brains_registry.py does, so none
of this ever talks to a real Supervisor process.
"""
import httpx
import pytest
from httpx import AsyncClient

from app.api.v1.routes.admin_sidecar import _supervisor_headers
from app.core.config import settings


# --- header construction (unit-level, no live server needed) ---------------
#
# Found live-testing this proxy against a genuine Supervisor: sending
# "Authorization: Bearer " (trailing space, nothing after it) for the blank-
# token default makes REAL httpx raise a LocalProtocolError on the illegal
# header value -- which the route's `except httpx.HTTPError` catches and
# reports as a misleading 502 SUPERVISOR_UNAVAILABLE for a supervisor that
# was actually reachable. The mocked AsyncClient below never exercises
# httpx's own header encoder, so it could not have caught this -- these two
# tests pin the header dict directly instead.


def test_headers_omit_authorization_when_token_blank(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SUPERVISOR_TOKEN", "")
    assert _supervisor_headers() == {}


def test_headers_include_bearer_token_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SUPERVISOR_TOKEN", "shh-secret")
    assert _supervisor_headers() == {"Authorization": "Bearer shh-secret"}


class _FakeSupervisorClient:
    """Stands in for httpx.AsyncClient. `responses` maps an HTTP method
    ("GET"/"POST") + path suffix ("/status", "/start", "/stop") to either an
    (status_code, json_body) tuple, or the string "unreachable" to simulate
    a connection failure."""

    responses: dict[tuple[str, str], object] = {}
    last_request: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def _call(self, method: str, url: str, **kwargs):
        suffix = "/" + url.rsplit("/", 1)[-1]
        _FakeSupervisorClient.last_request = {
            "method": method,
            "url": url,
            "headers": kwargs.get("headers"),
            "json": kwargs.get("json"),
        }
        outcome = _FakeSupervisorClient.responses.get((method, suffix))
        if outcome == "unreachable":
            raise httpx.ConnectError("connection refused", request=httpx.Request(method, url))
        status_code, body = outcome
        return httpx.Response(status_code, json=body, request=httpx.Request(method, url))

    async def get(self, url, **kwargs):
        return await self._call("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self._call("POST", url, **kwargs)


@pytest.fixture(autouse=True)
def _patch_httpx(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSupervisorClient)
    _FakeSupervisorClient.responses = {}
    _FakeSupervisorClient.last_request = None
    yield


# --- status -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_passes_through_supervisor_200(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("GET", "/status")] = (
        200,
        {
            "sidecar_running": True,
            "sidecar_health": "ok",
            "free_ram_gb": 8.5,
            "commit_used_gb": 12.0,
            "commit_total_gb": 32.0,
            "on_ac_power": True,
            "profile": "dev",
        },
    )
    resp = await client.get("/api/v1/admin/sidecar/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["sidecar_running"] is True
    assert resp.json()["profile"] == "dev"


@pytest.mark.asyncio
async def test_status_sends_bearer_token_from_settings(
    client: AsyncClient, admin_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "SUPERVISOR_TOKEN", "shh-secret")
    _FakeSupervisorClient.responses[("GET", "/status")] = (200, {"sidecar_running": False})

    await client.get("/api/v1/admin/sidecar/status", headers=admin_headers)

    assert _FakeSupervisorClient.last_request["headers"]["Authorization"] == "Bearer shh-secret"


@pytest.mark.asyncio
async def test_status_supervisor_unreachable_is_clean_502(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("GET", "/status")] = "unreachable"

    resp = await client.get("/api/v1/admin/sidecar/status", headers=admin_headers)

    assert resp.status_code == 502
    assert resp.json()["detail"]["error"]["code"] == "SUPERVISOR_UNAVAILABLE"


@pytest.mark.asyncio
async def test_status_requires_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/sidecar/status", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_status_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/admin/sidecar/status")
    assert resp.status_code == 403


# --- start ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_passes_through_200_with_pid(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/start")] = (200, {"pid": 4242, "profile": "dev"})

    resp = await client.post(
        "/api/v1/admin/sidecar/start",
        headers=admin_headers,
        json={"profile": "dev", "warm": True, "force": False},
    )

    assert resp.status_code == 200
    assert resp.json() == {"pid": 4242, "profile": "dev"}
    assert _FakeSupervisorClient.last_request["json"] == {
        "profile": "dev",
        "warm": True,
        "force": False,
    }


@pytest.mark.asyncio
async def test_start_defaults_warm_true_force_false(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/start")] = (200, {"pid": 1, "profile": "dev"})

    await client.post(
        "/api/v1/admin/sidecar/start", headers=admin_headers, json={"profile": "dev"}
    )

    assert _FakeSupervisorClient.last_request["json"] == {
        "profile": "dev",
        "warm": True,
        "force": False,
    }


@pytest.mark.asyncio
async def test_start_passes_through_409_already_running(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/start")] = (
        409,
        {"error": {"code": "ALREADY_RUNNING", "message": "sidecar already running"}},
    )

    resp = await client.post(
        "/api/v1/admin/sidecar/start", headers=admin_headers, json={"profile": "dev"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_start_passes_through_422_guard_refused(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/start")] = (
        422,
        {"error": {"code": "GUARD_REFUSED", "message": "not enough free RAM"}},
    )

    resp = await client.post(
        "/api/v1/admin/sidecar/start", headers=admin_headers, json={"profile": "prod"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_rejects_bad_profile(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/admin/sidecar/start", headers=admin_headers, json={"profile": "staging"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_supervisor_unreachable_is_clean_502(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/start")] = "unreachable"

    resp = await client.post(
        "/api/v1/admin/sidecar/start", headers=admin_headers, json={"profile": "dev"}
    )
    assert resp.status_code == 502
    assert resp.json()["detail"]["error"]["code"] == "SUPERVISOR_UNAVAILABLE"


# --- stop -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_passes_through_200(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/stop")] = (200, {"stopped": True})
    resp = await client.post("/api/v1/admin/sidecar/stop", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stop_passes_through_404_nothing_running(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/stop")] = (
        404,
        {"error": {"code": "NOT_RUNNING", "message": "nothing to stop"}},
    )
    resp = await client.post("/api/v1/admin/sidecar/stop", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_supervisor_unreachable_is_clean_502(client: AsyncClient, admin_headers: dict):
    _FakeSupervisorClient.responses[("POST", "/stop")] = "unreachable"
    resp = await client.post("/api/v1/admin/sidecar/stop", headers=admin_headers)
    assert resp.status_code == 502
    assert resp.json()["detail"]["error"]["code"] == "SUPERVISOR_UNAVAILABLE"
