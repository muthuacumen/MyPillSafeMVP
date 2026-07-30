"""Prescription-label OCR client (Priority 1B; rewritten Task A2.1).

PaddleOCR no longer runs inside this backend process/image at all -- on the
deploy target (a 4 GB droplet co-tenanted with a live site) that was a ~3 GB
image and a ~1.5 GB RAM spike per scan (measured ~2m21s CPU per label). The
work now happens on a team-run `dev/brains` sidecar reachable over the
private Tailscale tailnet (see `app/services/brains_registry.py`): this
module POSTs the uploaded image there and returns whatever text the sidecar
extracted.

Failure here is not degraded silently -- `OcrUnavailableError` is raised on
ANY failure (connection error, timeout, non-200 response, malformed JSON, or
a response missing `raw_text`) and the caller (`routes/prescriptions.py`)
turns that into an honest HTTP 503, never a fabricated prescription. See
that route's module docstring for the abstain-over-guess rationale.
"""
from __future__ import annotations

import logging

import httpx

from app.services.brains_registry import resolve_brains_url

logger = logging.getLogger(__name__)

# OCR is genuinely slow (subprocess spawn + model load + inference; measured
# ~10-45s on GPU depending on whether the sidecar's model cache is warm, and
# potentially much longer on a CPU-only sidecar) -- a short timeout here
# would manufacture failures for a pipeline that is actually still working.
OCR_TIMEOUT_SECONDS = 300.0

# FixbySonnet1 Task 4a: split connect from read. A down sidecar should fail
# fast (~5s) instead of taking as long as a slow-but-working one (measured:
# a 5-minute spinner with a flat timeout). The read side stays generous
# (OCR_TIMEOUT_SECONDS) because genuine in-progress OCR is legitimately slow.
_OCR_TIMEOUT = httpx.Timeout(OCR_TIMEOUT_SECONDS, connect=5.0)


class OcrUnavailableError(Exception):
    pass


async def extract_text(image_bytes: bytes, filename: str, content_type: str) -> str:
    """POST the prescription photo to the brains sidecar's
    `/ocr/prescription` and return its `raw_text`.

    Raises `OcrUnavailableError` on any failure -- connection error, timeout,
    non-200 status, malformed JSON, or a response missing `raw_text`. Never
    returns a fabricated/placeholder string; the caller decides what to do
    with a failure (Task A2.2: a user-safe 503, not demo text).
    """
    brains_url = await resolve_brains_url()

    try:
        async with httpx.AsyncClient(timeout=_OCR_TIMEOUT) as http_client:
            response = await http_client.post(
                f"{brains_url}/ocr/prescription",
                files={"image": (filename or "prescription.jpg", image_bytes, content_type or "image/jpeg")},
            )
    except httpx.HTTPError as exc:
        logger.warning("Brains sidecar unreachable for /ocr/prescription at %s: %s", brains_url, exc)
        raise OcrUnavailableError(f"Brains sidecar unreachable at {brains_url}: {exc}") from exc

    if response.status_code != 200:
        logger.warning(
            "Brains sidecar /ocr/prescription returned %s from %s: %s",
            response.status_code, brains_url, response.text,
        )
        raise OcrUnavailableError(
            f"Brains sidecar OCR failed ({response.status_code}) at {brains_url}: {response.text}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise OcrUnavailableError(f"Brains sidecar returned a non-JSON OCR response from {brains_url}") from exc

    raw_text = body.get("raw_text") if isinstance(body, dict) else None
    if raw_text is None:
        raise OcrUnavailableError(f"Brains sidecar OCR response from {brains_url} is missing 'raw_text'")

    return raw_text
