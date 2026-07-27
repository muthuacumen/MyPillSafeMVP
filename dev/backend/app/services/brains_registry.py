"""Sidecar pool: health-checked selection + admin pin override (Task A3).

Why: up to five team members may each run a `dev/brains` sidecar on their own
laptop. A closed laptop must not take the demo down -- this module picks a
healthy sidecar URL from a configured pool instead of hardcoding one.

Back-compat is the load-bearing rule here (A3.2 rule 1): when
`BRAINS_SERVICE_URLS` is unset/empty, `resolve_brains_url()` returns
`settings.BRAINS_SERVICE_URL` immediately with NO health check -- every
existing test and single-sidecar dev setup stays byte-identical in both
behaviour and latency. The pool machinery below only activates once a second
URL is actually configured.

Health-check state lives in plain module-level dicts (no DB, no extra
dependency) -- this is a small in-memory cache appropriate for a single
backend process, not a durable store.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

HEALTH_TIMEOUT_SECONDS = 2.0
HEALTH_CACHE_SECONDS = 30.0

# {url: {"healthy": bool, "latency_ms": float, "checked_at": iso-str, "_at": monotonic}}
_health_cache: dict[str, dict] = {}

# Admin-set pin (Task A3.4) -- process-local, not persisted. None = no pin.
_pinned_url: str | None = None


def configured_urls() -> list[str]:
    """The parsed `BRAINS_SERVICE_URLS` pool, in list order. Empty when the
    pool isn't configured (the back-compat single-URL path)."""
    raw = settings.BRAINS_SERVICE_URLS or ""
    return [u.strip() for u in raw.split(",") if u.strip()]


async def _check_health(url: str) -> dict:
    """`GET {url}/health`, 2s timeout, 200 = healthy. Cached 30s per URL.
    Never raises -- any connection/timeout error just means unhealthy."""
    now = time.monotonic()
    cached = _health_cache.get(url)
    if cached is not None and (now - cached["_at"]) < HEALTH_CACHE_SECONDS:
        return cached

    start = time.monotonic()
    healthy = False
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{url}/health")
            healthy = response.status_code == 200
    except Exception as exc:  # noqa: BLE001 -- health checking must never raise
        logger.debug("Brains pool health check failed for %s: %s", url, exc)
        healthy = False

    entry = {
        "healthy": healthy,
        "latency_ms": round((time.monotonic() - start) * 1000, 1),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "_at": time.monotonic(),
    }
    _health_cache[url] = entry
    return entry


async def resolve_brains_url() -> str:
    """Pick a sidecar URL to call this request.

    Rule 1 (back-compat, load-bearing): no pool configured -> return the
    single `BRAINS_SERVICE_URL` immediately, zero health-check latency.

    Rule 2: pool configured -> pinned URL if pinned AND healthy; else the
    first healthy URL in list order; else the first URL in the list (so a
    downstream 503 still names a concrete host).

    Rule 4: never raises -- any unexpected failure degrades to rule 2's
    last-resort fallback (first configured URL).
    """
    urls = configured_urls()
    if not urls:
        return settings.BRAINS_SERVICE_URL

    try:
        if _pinned_url and _pinned_url in urls:
            pin_health = await _check_health(_pinned_url)
            if pin_health["healthy"]:
                return _pinned_url

        for url in urls:
            health = await _check_health(url)
            if health["healthy"]:
                return url
    except Exception as exc:  # noqa: BLE001 -- rule 4: never raise
        logger.warning("Brains pool resolution failed, falling back to first configured URL: %s", exc)

    return urls[0]


async def pool_status() -> list[dict]:
    """`[{url, healthy, latency_ms, checked_at, pinned}]` for every
    configured URL (empty list when the pool isn't configured)."""
    statuses = []
    for url in configured_urls():
        health = await _check_health(url)
        statuses.append(
            {
                "url": url,
                "healthy": health["healthy"],
                "latency_ms": health["latency_ms"],
                "checked_at": health["checked_at"],
                "pinned": url == _pinned_url,
            }
        )
    return statuses


def set_pin(url: str | None) -> None:
    global _pinned_url
    _pinned_url = url


def get_pin() -> str | None:
    return _pinned_url
