"""Shared DIN format conversion — the ONE place that knows about both
DIN representations in play across the app x brains integration:

- **Canonical form** (what the app stores, `Prescription.din`, `String(8)`):
  an 8-digit zero-padded numeric string, e.g. ``"00013803"``. This is the
  standard Health Canada Drug Identification Number format.
- **SB2 token form** (what the brains sidecar speaks, both in
  `/reference/search` results and `/pill/analyze`'s `profile_dins` input):
  ``"DIN"`` + the *unpadded* integer, e.g. ``"DIN13803"`` — verified live
  against the sidecar (`GET /reference/search?q=GRAVOL` -> `din: "DIN13803"`).

Convert at the sidecar boundary with this pair, never inline elsewhere, so
the two representations can't drift out of sync (see
`documentation/integration/INTEGRATION_PLAN.md` Phase 2).
"""
from __future__ import annotations

import re

_CANONICAL_RE = re.compile(r"^\d{1,8}$")
_SB2_TOKEN_RE = re.compile(r"^DIN0*(\d{1,8})$", re.IGNORECASE)


def to_sb2_token(canonical_din: str) -> str:
    """Canonical 8-digit form -> SB2 token form.

    ``"00013803"`` -> ``"DIN13803"``. Raises `ValueError` if `canonical_din`
    isn't a 1-8 digit numeric string.
    """
    if not canonical_din or not _CANONICAL_RE.match(canonical_din):
        raise ValueError(f"Not a canonical DIN: {canonical_din!r}")
    return f"DIN{int(canonical_din)}"


def from_sb2_token(token: str) -> str:
    """SB2 token form -> canonical 8-digit zero-padded form.

    ``"DIN13803"`` -> ``"00013803"``. Raises `ValueError` if `token` isn't a
    ``"DIN" + digits`` string (case-insensitive prefix).
    """
    if not token:
        raise ValueError("DIN token is required")
    match = _SB2_TOKEN_RE.match(token.strip())
    if not match:
        raise ValueError(f"Not a valid SB2 DIN token: {token!r}")
    return match.group(1).zfill(8)


def normalize_din(value: str) -> str:
    """Validate + normalize user/API input that may arrive in either form
    (canonical 8-digit, possibly unpadded, OR the SB2 token form) into the
    canonical 8-digit zero-padded form the DB stores. Raises `ValueError`
    for anything that isn't a recognizable DIN.
    """
    if value is None:
        raise ValueError("DIN value is required")
    stripped = value.strip()
    if not stripped:
        raise ValueError("DIN value is required")
    if stripped.upper().startswith("DIN"):
        return from_sb2_token(stripped)
    if _CANONICAL_RE.match(stripped):
        return stripped.zfill(8)
    raise ValueError(f"Not a valid DIN: {value!r}")
