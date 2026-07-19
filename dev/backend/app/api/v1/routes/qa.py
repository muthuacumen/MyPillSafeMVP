"""BB3 Q&A + CB4 voice (Phase 4 of the app x brains integration).

`POST /api/v1/qa/chat` is patient-scoped (authenticated). Per the durable
2026-07-14 ADR decision, CB4 (a cloud Claude model, `app/services/
cb4_service.py`) is the production voice: BB3's sidecar resolves the query,
runs its deterministic short-circuits/guards, and (when generation would be
needed) hands back the packed, cited context instead of generating itself
-- CB4 generates the user-facing answer from that context, then BB3's
guards (via the sidecar's single-shot `/qa/guard`) run against CB4's output
with this module owning the retry protocol (see cb4_service.answer_question).

No key configured -> falls back to the sidecar's own local-7B generation
(`mode="full"`, BB3Engine.chat() verbatim) marked `voice: "local_7b"` --
this is BB3's self-contained default + eval harness, retained as the
offline fallback per BB3/CONTRACT.md's ARCHITECTURE DECISION note. That
path requires Ollama; a down Ollama surfaces as a clean 503, never a raw
500. See documentation/integration/INTEGRATION_PLAN.md Phase 4.
"""
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import get_current_patient
from app.core.config import settings
from app.models.user import User
from app.schemas.qa import QAChatRequest
from app.services import cb4_service, din_utils

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa"])

# Per spec: 60s context mode (sidecar resolve+retrieve+pack only, no LLM) /
# 180s full mode (sidecar's own local-7B generation via Ollama).
CONTEXT_MODE_TIMEOUT_SECONDS = 60.0
FULL_MODE_TIMEOUT_SECONDS = 180.0


def _brains_unreachable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": {
                "code": "BRAINS_UNAVAILABLE",
                "message": "The brains sidecar service could not be reached. Make sure it is running "
                f"at {settings.BRAINS_SERVICE_URL}.",
            }
        },
    )


def _din_bypass(din: str | None) -> str | None:
    """Canonical (or SB2-token) -> the sidecar's token form, exactly like
    routes/pill.py's profile-DIN conversion. Raises HTTPException(422) on a
    malformed DIN -- never silently drops it."""
    if not din:
        return None
    try:
        canonical = din_utils.normalize_din(din)
        return din_utils.to_sb2_token(canonical)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_DIN", "message": f"Not a valid DIN: {din!r}"}},
        ) from exc


@router.post("/chat")
async def qa_chat(
    body: QAChatRequest,
    _: Annotated[User, Depends(get_current_patient)],
):
    din_token = _din_bypass(body.din)

    if cb4_service.cb4_enabled():
        return await _context_mode(body, din_token)
    return await _full_mode(body, din_token)


async def _sidecar_qa_chat(body: QAChatRequest, din_token: str | None, mode: str, timeout: float) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            return await http_client.post(
                f"{settings.BRAINS_SERVICE_URL}/qa/chat",
                json={
                    "message": body.message,
                    "din": din_token,
                    "confirmed_name": body.confirmed_name,
                    "mode": mode,
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("Brains sidecar unreachable for /qa/chat (mode=%s): %s", mode, exc)
        raise _brains_unreachable_error() from exc


def _parse_sidecar_json(response: httpx.Response) -> dict:
    try:
        return response.json()
    except ValueError:
        return {"detail": {"error": {"code": "BRAINS_INVALID_RESPONSE", "message": response.text}}}


async def _context_mode(body: QAChatRequest, din_token: str | None):
    response = await _sidecar_qa_chat(body, din_token, "context", CONTEXT_MODE_TIMEOUT_SECONDS)
    payload = _parse_sidecar_json(response)

    if response.status_code != 200:
        # Sidecar's own error envelope already matches this app's shape --
        # pass it straight through, status code included (routes/pill.py idiom).
        return JSONResponse(status_code=response.status_code, content=payload)

    if payload.get("status") != "context_ready":
        # Short-circuit status (confirm/pick_list/not_found/no_entity/
        # enumeration/refused_dosing/empty-retrieval abstention) -- already
        # byte-identical to what BB3Engine.chat() would return.
        return {**payload, "voice": "none"}

    try:
        cb4_result = await cb4_service.answer_question(
            packed_sources=payload["packed_sources"],
            question=payload["question"],
            offered_tags=payload["offered_tags"],
            schema=payload["schema"],
            entity_names=payload["entity_names"],
            sources=payload["sources"],
            language=body.language,
        )
    except Exception as exc:  # noqa: BLE001 -- never let a CB4 failure surface as a raw 500
        logger.warning("CB4 generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "CB4_ERROR",
                    "message": "Couldn't generate an answer right now -- please try again.",
                }
            },
        ) from exc

    return {
        "status": cb4_result["status"],  # "answered" | "guard_refused"
        "resolution": payload["resolution"],
        "abstained": cb4_result["abstained"],
        "answer": cb4_result["answer"],
        "sources": payload["sources"],
        "tier": payload["tier"],
        "disclaimer": payload["disclaimer"],
        "cited_tags": cb4_result["cited_tags"],
        "priority": cb4_result["priority"],
        "guard_flags": cb4_result["guard_flags"],
        "refused_dosing": False,
        "voice": "cb4",
        "model": settings.LLM_MODEL,
    }


async def _full_mode(body: QAChatRequest, din_token: str | None):
    response = await _sidecar_qa_chat(body, din_token, "full", FULL_MODE_TIMEOUT_SECONDS)
    payload = _parse_sidecar_json(response)

    if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        error = (payload.get("detail") or {}).get("error") or {}
        if error.get("code") == "OLLAMA_UNAVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "code": "QA_OFFLINE_UNAVAILABLE",
                        "message": "Q&A isn't available right now -- no cloud key is configured on "
                        "this server and the offline fallback model isn't running. Please try "
                        "again later.",
                    }
                },
            )

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=payload)

    return payload
