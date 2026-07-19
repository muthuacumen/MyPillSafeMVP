"""Pill identification -- IMB1 (vision) + SB2 (deterministic matcher) via the
`dev/brains/` sidecar (Priority 6 / Phase 3 of the app x brains integration).

`/analyze/pill/v2` is the ONLY pill-scan endpoint (Phase 3 -- the legacy
OpenCV colour/shape + PaddleOCR-imprint + `din_pills` path was removed
entirely, per the owner's decision that supersedes the integration plan's
"keep behind a legacy flag"). `PILL_V2_ENABLED` is now a pure kill-switch:
off -> 501 `PILL_V2_DISABLED`; on (the default) -> proxy to the sidecar.
See `documentation/integration/INTEGRATION_PLAN.md` Phase 3.
"""
import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.services import brains_client, din_utils, prescription_service
from app.services.patient_service import get_patient_by_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])

_NO_PROFILE_MESSAGE = (
    "Pill checking works against your confirmed medications, and you don't have any yet. "
    "Scan a prescription and confirm its DIN first, then come back to check a pill."
)


def _sb2_token_to_canonical(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return din_utils.from_sb2_token(token)
    except ValueError:
        # Defensive only -- the sidecar's own reference table is the source
        # of every token we'd see here, so this should never actually fire.
        return token


def _enrich_ranked_candidates(ranked_raw: list, details_by_token: dict[str, dict]) -> list[dict]:
    enriched: list[dict] = []
    for item in ranked_raw or []:
        if not item or len(item) < 3:
            continue
        token, score, breakdown = item[0], item[1], item[2]
        details = details_by_token.get(token, {})
        enriched.append(
            {
                "din": _sb2_token_to_canonical(token),
                "score": score,
                "breakdown": breakdown,
                "product": details.get("product"),
                "strength": details.get("strength"),
                "active_ingredient": details.get("ai"),
            }
        )
    return enriched


@router.post("/pill/v2")
async def analyze_pill_v2(
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    image: UploadFile = File(...),
):
    """Proxy to the brains sidecar (IMB1_v0 detect+attributes -> SB2 verify/
    reject/abstain matcher), flag-gated behind `PILL_V2_ENABLED`.

    The patient's profile DINs are the *confirmed* DINs (`din_confirmed`)
    of their ACTIVE prescriptions (Phase 2), converted from the app's
    canonical 8-digit form to the SB2 sidecar's token form
    (`din_utils.to_sb2_token`) -- unconfirmed suggestions never leak into
    matching.

    Empty-profile short-circuit (Phase 3): if the patient has zero
    confirmed-DIN active prescriptions, the sidecar is never called --
    there is nothing to verify against -- and a distinct `no_profile`
    payload is returned instead.
    """
    if not settings.PILL_V2_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "code": "PILL_V2_DISABLED",
                    "message": "The brains sidecar integration (IMB1+SB2) is not enabled on this server. "
                    "Set PILL_V2_ENABLED=true and run dev/brains' sidecar service to use this endpoint.",
                }
            },
        )

    profile_dins: list[str] = []
    patient = await get_patient_by_user_id(db, current_user.id)
    if patient:
        prescriptions = await prescription_service.list_active_for_patient(db, patient.id)
        profile_dins = [
            din_utils.to_sb2_token(rx.din)
            for rx in prescriptions
            if rx.din_confirmed and rx.din
        ]

    if not profile_dins:
        # Do NOT call the sidecar -- there is no profile to verify against.
        return {
            "status": "no_profile",
            "message": _NO_PROFILE_MESSAGE,
            "record": None,
            "match": None,
        }

    image_bytes = await image.read()

    try:
        async with httpx.AsyncClient(timeout=180.0) as http_client:
            response = await http_client.post(
                f"{settings.BRAINS_SERVICE_URL}/pill/analyze",
                files={"image": (image.filename or "pill.jpg", image_bytes, image.content_type or "image/jpeg")},
                data={"profile_dins": json.dumps(profile_dins)},
            )
    except httpx.HTTPError as exc:
        logger.warning("Brains sidecar unreachable at %s: %s", settings.BRAINS_SERVICE_URL, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "BRAINS_UNAVAILABLE",
                    "message": "The brains sidecar service could not be reached. Make sure it is running "
                    f"at {settings.BRAINS_SERVICE_URL}.",
                }
            },
        ) from exc

    try:
        body = response.json()
    except ValueError:
        body = {"detail": {"error": {"code": "BRAINS_INVALID_RESPONSE", "message": response.text}}}

    if response.status_code != 200:
        # Sidecar's own error envelope already matches this app's shape --
        # pass it straight through, status code included.
        return JSONResponse(status_code=response.status_code, content=body)

    record = body.get("record") or {}
    raw_match = body.get("match")

    enriched_match: dict | None = None
    if raw_match:
        ranked_raw = raw_match.get("ranked_candidates") or []
        tokens_needed = sorted({item[0] for item in ranked_raw if item and item[0]})
        details_by_token = await brains_client.get_reference_candidates(tokens_needed) if tokens_needed else {}
        enriched_match = {
            "decision": raw_match.get("decision"),
            "matched_din": _sb2_token_to_canonical(raw_match.get("matched_din")),
            "abstain_action": raw_match.get("abstain_action"),
            "disclaimer": raw_match.get("disclaimer"),
            "ranked_candidates": _enrich_ranked_candidates(ranked_raw, details_by_token),
        }

    # Persist the scan outcome for the Safety Records surface (Phase 3) --
    # one row per pill scan. The uploaded image itself is never stored here
    # (image_filename only, matching the existing Analysis idiom).
    top_candidate = (
        enriched_match["ranked_candidates"][0]
        if enriched_match and enriched_match["ranked_candidates"]
        else None
    )
    scan_row = Analysis(
        user_id=current_user.id,
        status="completed",
        image_filename=image.filename,
        pills_detected=[],
        label_info={},
        guidance=None,
        safety_alerts=[],
        ml_pipeline_enabled=False,
        detected=bool(record.get("detected")),
        decision=enriched_match["decision"] if enriched_match else None,
        abstain_action=enriched_match["abstain_action"] if enriched_match else None,
        matched_din=enriched_match["matched_din"] if enriched_match else None,
        top_candidate_score=top_candidate["score"] if top_candidate else None,
        top_candidate_breakdown=top_candidate["breakdown"] if top_candidate else None,
        shadow_fusion_suspected=record.get("shadow_fusion_suspected"),
    )
    db.add(scan_row)
    await db.flush()

    return {"status": "ok", "record": record, "match": enriched_match}
