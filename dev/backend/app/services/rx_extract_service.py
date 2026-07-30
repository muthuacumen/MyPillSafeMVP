"""Client for the brains sidecar's `POST /rx/extract` (FixbyOPUS3 Task A3).

Mirrors `ocr_service.extract_text` exactly: the model lives on the ML tier,
this backend only speaks HTTP to it, and ANY failure raises a typed error
rather than degrading silently. The difference is what the caller does with
that failure -- OCR failure is fatal to the scan (there is no honest way to
invent label text), whereas an extraction failure has a real fallback: the
deterministic regex proposer. Both then go through the SAME guardrails and
the SAME server-side time derivation, so a fallback changes which proposer
spoke, never which safety rules applied.
"""
from __future__ import annotations

import logging

import httpx

from app.services.brains_registry import resolve_brains_url

logger = logging.getLogger(__name__)

# The sidecar caps itself at 60 s of Ollama time (corrective retry included);
# a little headroom on top so a sidecar that is about to answer isn't cut off
# by the client. Connect stays short so a DOWN sidecar falls back to regex in
# ~5 s instead of making the user wait out the read timeout.
RX_EXTRACT_TIMEOUT_SECONDS = 75.0
_RX_EXTRACT_TIMEOUT = httpx.Timeout(RX_EXTRACT_TIMEOUT_SECONDS, connect=5.0)


class RxExtractUnavailableError(Exception):
    pass


async def extract_medications(raw_text: str) -> dict:
    """POST `raw_text` to the sidecar and return its
    `{medications, model, elapsed_seconds}` payload.

    Raises `RxExtractUnavailableError` on connection error, timeout, non-200
    status, non-JSON body, or a body without a `medications` list. Never
    returns a fabricated medication list -- the caller falls back to the
    regex proposer, which is honest degradation, not invention.
    """
    brains_url = await resolve_brains_url()

    try:
        async with httpx.AsyncClient(timeout=_RX_EXTRACT_TIMEOUT) as http_client:
            response = await http_client.post(
                f"{brains_url}/rx/extract",
                json={"raw_text": raw_text},
            )
    except httpx.HTTPError as exc:
        logger.warning("Brains sidecar unreachable for /rx/extract at %s: %s", brains_url, exc)
        raise RxExtractUnavailableError(f"Brains sidecar unreachable at {brains_url}: {exc}") from exc

    if response.status_code != 200:
        logger.warning(
            "Brains sidecar /rx/extract returned %s from %s: %s",
            response.status_code, brains_url, response.text[:500],
        )
        raise RxExtractUnavailableError(
            f"Brains sidecar rx extraction failed ({response.status_code}) at {brains_url}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise RxExtractUnavailableError(
            f"Brains sidecar returned a non-JSON /rx/extract response from {brains_url}"
        ) from exc

    if not isinstance(body, dict) or not isinstance(body.get("medications"), list):
        raise RxExtractUnavailableError(
            f"Brains sidecar /rx/extract response from {brains_url} has no 'medications' list"
        )

    return body
