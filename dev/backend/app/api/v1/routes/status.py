"""Public system-status endpoints (Task T2) -- no auth, meant to be polled by
the frontend's sidecar-status ticker.

`GET /status/sidecar` answers one question -- "would a scan work right now?"
-- by calling `brains_registry.is_sidecar_healthy()`, which force-refreshes
its own `/health` probe on every call (it deliberately bypasses
brains_registry's 30s per-URL health cache). A 20s in-process cache sits in
front of THAT here, so a ticker polling every few seconds doesn't turn into
request pressure on the sidecar -- and because the underlying probe is
always fresh, this route's own 20s cache is the ONLY staleness bound on what
the ticker reports (not 20s stacked on top of a stale-by-up-to-30s reading).

This is NOT the same check `/analyze/pill/v2` and `/tray/analyze` pay for.
Those call `resolve_brains_url()`, which in the default single-sidecar setup
(`BRAINS_SERVICE_URLS` unset) returns the configured URL immediately with NO
health check at all (back-compat, A3.2 rule 1) -- so in that common mode the
analyze routes never health-check the sidecar. This endpoint is the one
place that always does.
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services import brains_registry

router = APIRouter(prefix="/status", tags=["status"])

_CACHE_SECONDS = 20.0
# Module-level, like brains_registry's own cache -- a single backend
# process, no DB, no extra dependency.
_cached_payload: dict | None = None
_cached_at: float = 0.0


class SidecarStatusResponse(BaseModel):
    sidecar_up: bool
    message: str
    checked_at: str


@router.get("/sidecar", response_model=SidecarStatusResponse)
async def public_sidecar_status() -> SidecarStatusResponse:
    global _cached_payload, _cached_at

    now = time.monotonic()
    if _cached_payload is not None and (now - _cached_at) < _CACHE_SECONDS:
        return SidecarStatusResponse(**_cached_payload)

    # is_sidecar_healthy() force-refreshes past brains_registry's own 30s
    # cache -- this 20s cache above is the only staleness this route adds.
    sidecar_up = await brains_registry.is_sidecar_healthy()
    payload = {
        "sidecar_up": sidecar_up,
        "message": settings.SIDECAR_UP_MESSAGE if sidecar_up else settings.SIDECAR_DOWN_MESSAGE,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    _cached_payload = payload
    _cached_at = now
    return SidecarStatusResponse(**payload)
