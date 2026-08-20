"""Admin sidecar-supervisor proxy (Task T2).

The backend does NOT start, stop, or warm the `dev/brains` sidecar itself --
a separate Supervisor service (dev/ops, default port 8090) owns that job and
can see host resources (free RAM, AC power, commit charge) this process has
no business touching. Every route below is a thin, admin-gated PROXY: it
forwards the request to `{SUPERVISOR_URL}{/status,/start,/stop}` with a
bearer token and passes the Supervisor's own status code and JSON body
straight back through, unwrapped -- Admin -> Sidecar in the frontend renders
exactly what the Supervisor said, not this backend's opinion of it.

Supervisor contract (owned by the Supervisor build, documented here only so
the proxy's expectations are legible in one place):
  GET  /status -> 200 {sidecar_running, sidecar_health, free_ram_gb,
                        commit_used_gb, commit_total_gb, on_ac_power, profile}
  POST /start  -> 200 {pid, profile} | 409 already running | 422 guard-refused
  POST /stop   -> 200 | 404 nothing running

A Supervisor that can't be reached at all (not running, wrong port, network
blip) is reported as 502 with a clear detail -- never a bare 500 stack, since
"the Supervisor is down" is an expected, everyday admin-facing state, not a
bug in this backend.
"""
import logging
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import get_current_admin
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/sidecar", tags=["admin"])

# Status must come back fast -- it's what an admin's dashboard polls. Not as
# fast as it used to be, though: the Supervisor's own /health proxy to the
# sidecar was raised from 3.0s to SUPERVISOR_HEALTH_TIMEOUT_S (default 8.0s,
# RP4 defect C -- the sidecar's /health synchronously calls BB3's
# ollama_up(), measured at ~4.14s to fail when Ollama is down, a normal
# state, not an error) so a /status that legitimately takes up to ~8s is now
# routine, not a hang -- 5.0s here would 502 on exactly that routine case.
_STATUS_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
# Start can legitimately take a while: `warm=true` means the Supervisor
# loads the model into memory before it answers, which is the whole point of
# warming it ahead of a demo instead of eating that latency on the first
# real request.
_START_TIMEOUT = httpx.Timeout(120.0, connect=5.0)
# Stop is not contractually instant either (graceful process teardown), but
# has no reason to run anywhere near as long as a model warm-up -- a
# generous middle ground rather than reusing either extreme.
_STOP_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class SidecarStartRequest(BaseModel):
    profile: Literal["dev", "prod"] = "dev"
    warm: bool = True
    force: bool = False


def _supervisor_headers() -> dict[str, str]:
    # Omit the header entirely when SUPERVISOR_TOKEN is blank (the local-dev
    # default) rather than sending "Bearer " with a trailing space and
    # nothing after it -- httpx's own header validation rejects that as an
    # illegal header value (a real bug found live-testing this proxy against
    # a genuine Supervisor: it surfaced as a misleading 502
    # SUPERVISOR_UNAVAILABLE for a supervisor that was, in fact, reachable
    # and simply not sent any credential). A Supervisor with no auth
    # configured doesn't need the header at all; one that requires auth
    # correctly 401s a request that sends none, same as any other bearer-
    # token API.
    if not settings.SUPERVISOR_TOKEN:
        return {}
    return {"Authorization": f"Bearer {settings.SUPERVISOR_TOKEN}"}


def _unreachable(exc: Exception) -> HTTPException:
    logger.warning("Sidecar Supervisor unreachable at %s: %s", settings.SUPERVISOR_URL, exc)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "SUPERVISOR_UNAVAILABLE",
                "message": (
                    "The sidecar supervisor could not be reached at "
                    f"{settings.SUPERVISOR_URL}. Make sure it is running."
                ),
            }
        },
    )


def _passthrough(response: httpx.Response) -> JSONResponse:
    """Forward the Supervisor's own status code and body verbatim -- this
    proxy has no opinion of its own about what 409/422/404 mean here."""
    try:
        body = response.json()
    except ValueError:
        body = {
            "error": {
                "code": "SUPERVISOR_INVALID_RESPONSE",
                "message": response.text,
            }
        }
    return JSONResponse(status_code=response.status_code, content=body)


@router.get("/status")
async def sidecar_status(_: Annotated[User, Depends(get_current_admin)]) -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=_STATUS_TIMEOUT) as client:
            response = await client.get(
                f"{settings.SUPERVISOR_URL}/status", headers=_supervisor_headers()
            )
    except httpx.HTTPError as exc:
        raise _unreachable(exc) from exc
    return _passthrough(response)


@router.post("/start")
async def sidecar_start(
    payload: SidecarStartRequest,
    _: Annotated[User, Depends(get_current_admin)],
) -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=_START_TIMEOUT) as client:
            response = await client.post(
                f"{settings.SUPERVISOR_URL}/start",
                headers=_supervisor_headers(),
                json=payload.model_dump(),
            )
    except httpx.HTTPError as exc:
        raise _unreachable(exc) from exc
    return _passthrough(response)


@router.post("/stop")
async def sidecar_stop(_: Annotated[User, Depends(get_current_admin)]) -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=_STOP_TIMEOUT) as client:
            response = await client.post(
                f"{settings.SUPERVISOR_URL}/stop", headers=_supervisor_headers()
            )
    except httpx.HTTPError as exc:
        raise _unreachable(exc) from exc
    return _passthrough(response)
