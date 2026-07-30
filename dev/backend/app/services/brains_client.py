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
import re

import httpx

from app.services import din_utils
from app.services.brains_registry import resolve_brains_url

logger = logging.getLogger(__name__)

# --- Query hygiene (2026-07-29 SA finding) ----------------------------------
#
# The sidecar matches with rapidfuzz `WRatio` and NO score cutoff, so it
# always returns its top-N however bad they are, and WRatio's partial-ratio
# component scores ~85 for any product merely containing "TABLET"/"MG".
# Strength and dosage-form tokens therefore do not just fail to help -- they
# actively dilute the real drug token until generic words win. Measured:
# `"DIGOXIN 0.125 MG TABLET 0.125 mg"` returned ALDACTONE / OVOL FOR GAS,
# while the bare name `"DIGOXIN"` returns digoxin products; a nonsense query
# `"ZZZQQQ 25 MG TAB"` returned the same confident 85.5 candidates. Because
# `flag_not_in_reference` only fires on an EMPTY list, that junk reached the
# user with no warning at all -- and a wrongly linked DIN is worse than none
# (it feeds SB2 a wrong appearance row and BB3 a wrong monograph).
#
# The brand/product index carries no strength or form information worth
# matching against, so stripping both is pure gain on the matching side. The
# strength is not discarded -- it is reapplied as a RANKING hint below, which
# is strictly better than using it as a match token.
_STRENGTH_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|ug|g|ml|l|iu|u|%|units?)\b(?:\s*/\s*\w+)?",
    re.I,
)
_FORM_RE = re.compile(
    r"\b(?:tablets?|tabs?|caplets?|capsules?|caps?|softgels?|gelcaps?|"
    r"injections?|solutions?|suspensions?|syrups?|creams?|ointments?|"
    r"patch(?:es)?|inhalers?|drops?|suppositor(?:y|ies)|sprays?|"
    r"powders?|lotions?|gels?|elixirs?)\b",
    re.I,
)
_PER_UNIT_RE = re.compile(r"\b\d+\s*/\s*\w+\b")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def clean_search_query(text: str) -> str:
    """Strip strength + dosage-form tokens from a medication name.

    Falls back to the original text when stripping would leave nothing (a
    name that is *only* a strength), so this can never turn a searchable
    query into an empty one.
    """
    q = _PER_UNIT_RE.sub(" ", text or "")
    q = _STRENGTH_RE.sub(" ", q)
    q = _FORM_RE.sub(" ", q)
    q = re.sub(r"[^\w\s/-]", " ", q)
    q = re.sub(r"\s+", " ", q).strip(" -/")
    return q or (text or "").strip()


def _strength_key(strength: str | None) -> set[str]:
    return set(_NUM_RE.findall(str(strength or "").replace(",", ".")))


def _rerank_by_strength(rows: list[dict], strength_hint: str | None) -> list[dict]:
    """Stable re-rank putting candidates whose strength matches the label's
    strength first.

    The sidecar returns exact-name matches all tied at the same score, so its
    ordering among them is arbitrary: searching "MOTRIN" put MOTRIN 200MG at
    rank 1 and the label's MOTRIN 400MG at rank 5. The correct variant was
    always present, just not first. Same for ASPIRIN 81MG (rank 4), GRAVOL
    TABLETS (rank 2) and PMS-DIGOXIN 0.125 MG (rank 4).
    """
    wanted = _strength_key(strength_hint)
    if not wanted:
        return rows
    return sorted(rows, key=lambda r: 0 if _strength_key(r.get("strength")) & wanted else 1)

# Short timeout: this call happens inline during prescription upload and
# must never make the user wait long for something that's allowed to fail.
SUGGESTION_TIMEOUT_SECONDS = 3.0

# Also short: this runs inline after a pill-scan analysis, purely to attach
# display names to candidates the matcher already scored -- cosmetic, not a
# hard dependency of the decision itself.
CANDIDATES_TIMEOUT_SECONDS = 5.0


async def search_reference(
    q: str, limit: int = 10, strength_hint: str | None = None
) -> list[dict]:
    """Fuzzy product-name search proxied to the sidecar's /reference/search.

    The query is passed through `clean_search_query` first -- strength and
    dosage-form tokens are stripped, because they carry no naming signal for
    the brand index and measurably dilute the real drug token (see that
    function's comment for the digoxin case). `strength_hint`, when given,
    is used to re-rank the *results* so the label's own strength surfaces
    first among otherwise score-tied variants. Callers pass the medication's
    parsed dosage; it is a ranking signal, never a filter, so a strength the
    reference spells differently can never hide a correct product.

    Returns `[{"din": <canonical 8-digit>, "product", "strength", "score",
    "pill_verifiable"}]` -- DIN tokens converted from the sidecar's
    `"DIN13803"` form to the app's canonical `"00013803"` form here, once,
    at the boundary.

    `pill_verifiable` (Task B2) says whether the DIN is in the 7,055-DIN
    appearance tier as well as the 11,609-DIN profile tier -- i.e. whether a
    photo can ever verify it. Absent from an older sidecar's reply, it comes
    back `None` (unknown), never `False`: "we could not ask" must not render
    as "this medication cannot be checked".

    Returns `[]` on any failure: sidecar down, slow (past
    `SUGGESTION_TIMEOUT_SECONDS`), unreachable, or a non-list/invalid JSON
    reply. Never raises.
    """
    if not q or not q.strip():
        return []

    cleaned = clean_search_query(q)

    try:
        brains_url = await resolve_brains_url()
        async with httpx.AsyncClient(timeout=SUGGESTION_TIMEOUT_SECONDS) as http_client:
            response = await http_client.get(
                f"{brains_url}/reference/search",
                params={"q": cleaned, "limit": limit},
            )
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Brains sidecar reference search failed (q=%r): %s", cleaned, exc)
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
        raw_verifiable = item.get("pill_verifiable")
        results.append(
            {
                "din": canonical,
                "product": item.get("product") or "",
                "strength": item.get("strength"),
                "score": item.get("score", 0.0),
                "pill_verifiable": (
                    None if raw_verifiable is None else bool(raw_verifiable)
                ),
            }
        )
    return _rerank_by_strength(results, strength_hint)


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


async def get_profile_rows(dins: list[str]) -> dict[str, dict] | None:
    """PROFILE-tier lookup (FixbyOPUS3 Task B3) for a set of SB2 token-form
    DINs, proxied to the sidecar's `/reference/profile`.

    Returns `{token_din: row}` -- rows carry `pill_verifiable`. Returns
    **None**, not `{}`, when the sidecar could not be reached or answered
    badly. That distinction is the whole point of this function: an empty
    dict means "these DINs are genuinely not in the profile tier", whereas
    None means "we do not know", and the caller must not turn "we do not
    know" into a "this medication can't be photo-checked" badge.
    """
    if not dins:
        return {}

    try:
        brains_url = await resolve_brains_url()
        async with httpx.AsyncClient(timeout=CANDIDATES_TIMEOUT_SECONDS) as http_client:
            response = await http_client.get(
                f"{brains_url}/reference/profile",
                params={"dins": ",".join(dins)},
            )
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Brains sidecar profile lookup failed (dins=%r): %s", dins, exc)
        return None

    if not isinstance(raw, list):
        return None

    return {row["din"]: row for row in raw if isinstance(row, dict) and row.get("din")}
