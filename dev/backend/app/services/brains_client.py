"""Thin, failure-tolerant HTTP client for the dev/brains sidecar's
`/reference/search` endpoint.

Used from three places:
- prescription create (`routes/prescriptions.py`), to attach `din_suggestions`
  to each newly parsed medication block;
- the authenticated proxy route (`routes/reference.py`), for the frontend's
  "pick a different one" / edit-medication DIN search box;
- the pill-scan proxy (`routes/pill.py`), to enrich SB2's `ranked_candidates`
  (DIN + score only) with a display name/strength for the UI (Phase 3).

DIN linking is an enhancement, never a save blocker (Phase 2 spec): every
function here degrades to an empty result on timeout, connection error, or a
malformed reply -- it never raises.
"""
from __future__ import annotations

import logging

import httpx

from app.services import din_utils
from app.services.brains_registry import resolve_brains_url

logger = logging.getLogger(__name__)

# Short timeout: this call happens inline during prescription upload and
# must never make the user wait long for something that's allowed to fail.
SUGGESTION_TIMEOUT_SECONDS = 3.0

# Also short: this runs inline after a pill-scan analysis, purely to attach
# display names to candidates the matcher already scored -- cosmetic, not a
# hard dependency of the decision itself.
CANDIDATES_TIMEOUT_SECONDS = 5.0


async def search_reference(q: str, limit: int = 10) -> list[dict]:
    """Fuzzy product-name search proxied to the sidecar's /reference/search.

    Returns `[{"din": <canonical 8-digit>, "product", "strength", "score"}]`
    -- DIN tokens converted from the sidecar's `"DIN13803"` form to the
    app's canonical `"00013803"` form here, once, at the boundary.

    Returns `[]` on any failure: sidecar down, slow (past
    `SUGGESTION_TIMEOUT_SECONDS`), unreachable, or a non-list/invalid JSON
    reply. Never raises.
    """
    if not q or not q.strip():
        return []

    try:
        brains_url = await resolve_brains_url()
        async with httpx.AsyncClient(timeout=SUGGESTION_TIMEOUT_SECONDS) as http_client:
            response = await http_client.get(
                f"{brains_url}/reference/search",
                params={"q": q, "limit": limit},
            )
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Brains sidecar reference search failed (q=%r): %s", q, exc)
        return []

    if not isinstance(raw, list):
        return []

    results: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        token = item.get("din")
        if not token:
            continue
        try:
            canonical = din_utils.from_sb2_token(str(token))
        except ValueError:
            logger.warning("Sidecar returned a non-DIN token, skipping: %r", token)
            continue
        results.append(
            {
                "din": canonical,
                "product": item.get("product") or "",
                "strength": item.get("strength"),
                "score": item.get("score", 0.0),
            }
        )
    return results


async def get_reference_candidates(dins: list[str]) -> dict[str, dict]:
    """Fetch reference rows (product/strength/active ingredient/etc) for a
    set of SB2 *token-form* DINs (e.g. ``"DIN13803"``), proxied to the
    sidecar's `/reference/candidates`. Used to enrich `match_pill`'s
    `ranked_candidates` -- which carries only `(din, score, breakdown)` --
    with something a UI can actually display.

    Returns `{token_din: row_dict}`. Never raises: an empty dict on any
    failure (down sidecar, timeout, malformed reply) just means the pill
    result renders without product names -- the decision itself is
    unaffected.
    """
    if not dins:
        return {}

    try:
        brains_url = await resolve_brains_url()
        async with httpx.AsyncClient(timeout=CANDIDATES_TIMEOUT_SECONDS) as http_client:
            response = await http_client.get(
                f"{brains_url}/reference/candidates",
                params={"dins": ",".join(dins)},
            )
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Brains sidecar reference candidates lookup failed (dins=%r): %s", dins, exc)
        return {}

    if not isinstance(raw, list):
        return {}

    return {row["din"]: row for row in raw if isinstance(row, dict) and row.get("din")}
