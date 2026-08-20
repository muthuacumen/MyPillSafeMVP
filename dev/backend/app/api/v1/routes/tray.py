"""Tray scan -- one photo of a weekly organiser, N per-SLOT verdicts.

`POST /api/v1/tray/analyze` is the tray sibling of `/analyze/pill/v2`. It
deliberately reuses that route's idioms verbatim -- `get_current_patient`
auth, `resolve_brains_url()` + `httpx.AsyncClient`, the BRAINS_UNAVAILABLE 503
envelope, sidecar-error passthrough, and one `Analysis` row per scanned pill --
because a second, subtly different set of conventions is how error handling
rots.

WHAT IS DIFFERENT FROM THE SINGLE-PILL ROUTE
--------------------------------------------
1. The sidecar returns SIX WELLS; the patient sees SIX SLOTS. `slot = well + 1`
   (Muthu's filed tray call 2). The frontend never does that arithmetic.
2. Every slot carries its own alert payload and the pharmacist hedge (same
   call). Empty slots included -- a grid with a hole in it is worse than a
   grid that says "empty".
3. Profile DINs are filtered against the C8 allowlist BEFORE the call (Muthu's
   session decision D-2). An excluded medication is never scored, because
   scoring it is the only way it could ever come back `verify`. There is NO
   per-slot "this pill is unsupported" -- that would be identification, and
   this system verifies rather than identifies. Excluded meds get a
   profile-level notice and nothing else.
4. NONE (no markings on any photographed face) routes to Flip/Reshoot
   alongside UNREADABLE (Muthu's filed tray call 3), NOT to the single-pill
   terminal message. Whether that loop should eventually become terminal is
   PENDING with Muthu and is a request parameter, defaulted to `retry`.

The reader batching that makes six wells affordable is the sidecar's business
(filed tray call 1). Nothing here batches anything.
"""
import json
import logging
import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.services import din_utils, nb08_messages, prescription_service, tray_messages
from app.services.allowlist import get_allowlist
from app.services.brains_registry import resolve_brains_url
from app.services.patient_service import get_patient_by_user_id
from app.services.tray_messages import NoneRoute

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tray", tags=["tray"])


def _sb2_token_to_canonical(token: str | None) -> str | None:
    """Sidecar token form -> the app's canonical 8-digit form, at the boundary,
    once. Mirrors routes/pill.py deliberately; the defensive fallback exists
    for the same reason it does there."""
    if not token:
        return None
    try:
        return din_utils.from_sb2_token(token)
    except ValueError:
        return token


def _frame_message(profile_dins: list[str], allowlist) -> tray_messages.nb08_messages.MessageSet:
    """The frame-level C.6 verdict for the two paths that never photograph
    anything the sidecar could score: an empty profile, and a profile where
    nothing at all is covered.

    `resolve` checks the profile BEFORE it touches the record, so passing an
    empty record here is not a trick -- those two branches are reached without
    the record being read at all.
    """
    empty = tray_messages.nb08_record.PillRecord(detected=False, photo="")
    return nb08_messages.resolve(empty, profile_dins=profile_dins, allowlist=allowlist)


def _distinct_medications(tokens: list[str]) -> list[str]:
    """The profile as DISTINCT medications, order preserved.

    Coverage is a question about MEDICATIONS, not about prescription rows: two
    active prescriptions of one DIN are one medication this build can or cannot
    verify. `allowlist.unsupported()` already dedupes, so counting it against a
    raw row count mixed two bases and told a patient with two prescriptions of
    one excluded drug "1 of 2 not covered" -- while the very next branch
    short-circuited on 0 supported and said the whole profile was uncovered.
    Dedupe ONCE, here, so every downstream consumer shares the basis.
    """
    return list(dict.fromkeys(tokens))


def _profile_block(profile_dins: list[str], allowlist) -> dict[str, Any]:
    unsupported = allowlist.unsupported(profile_dins)
    supported = allowlist.supported_subset(profile_dins)
    notice = None
    # A partially covered profile gets the anonymous count-only note. A fully
    # uncovered one does not -- there the note is promoted to the primary
    # frame message instead, so emitting both would say it twice.
    if unsupported and len(unsupported) != len(profile_dins):
        notice = {
            "key": nb08_messages.MsgKey.UNSUPPORTED_NOTE,
            "params": {"unsupported_n": len(unsupported), "profile_n": len(profile_dins)},
            "default_en": nb08_messages._EN[nb08_messages.MsgKey.UNSUPPORTED_NOTE],
            "provisional": False,
        }
    return {
        "profile_n": len(profile_dins),
        "supported_n": len(supported),
        "unsupported_n": len(unsupported),
        "notice": notice,
    }


@router.post("/analyze")
async def analyze_tray(
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    photo: UploadFile = File(...),
    none_route: str | None = Form(default=None),
):
    """Proxy one tray frame to the sidecar's `/tray/analyze` and return one
    verdict per slot.

    `none_route` is the retry-vs-terminal switch for the tray NONE loop. It is
    a PARAMETER, not a decision: Muthu has not ruled on when (or whether) the
    flip/reshoot loop should stop, and this route must not rule on it either.
    Absent -> `settings.TRAY_NONE_ROUTE` -> `"retry"`.
    """
    if not settings.TRAY_ANALYZE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "code": "TRAY_ANALYZE_DISABLED",
                    "message": "Tray scanning is not enabled on this server. "
                    "Set TRAY_ANALYZE_ENABLED=true and run the brains sidecar to use this endpoint.",
                }
            },
        )

    route = (none_route or settings.TRAY_NONE_ROUTE or NoneRoute.DEFAULT).strip().lower()
    if route not in NoneRoute.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "TRAY_BAD_NONE_ROUTE",
                    "message": f"none_route must be one of {sorted(NoneRoute.ALL)}.",
                }
            },
        )

    allowlist = get_allowlist()

    # --- profile: canonical 8-digit -> SB2 token form, ONCE, via din_utils ---
    # The documented trap: the reference keys on the UNPADDED integer, so a
    # padded token yields an empty ballot and SB2 returns a `reject` that is
    # indistinguishable from a genuine rejection. Never hand-roll this.
    profile_dins: list[str] = []
    patient = await get_patient_by_user_id(db, current_user.id)
    if patient:
        prescriptions = await prescription_service.list_active_for_patient(db, patient.id)
        profile_dins = _distinct_medications([
            din_utils.to_sb2_token(rx.din) for rx in prescriptions if rx.din_confirmed and rx.din
        ])

    profile_block = _profile_block(profile_dins, allowlist)

    if not profile_dins:
        frame = _frame_message(profile_dins, allowlist)
        return {
            "status": "no_profile",
            "tray": False,
            "pipeline": None,
            "slot_count": tray_messages.SLOT_COUNT,
            "none_route": route,
            "message": tray_messages.msg_to_dict(frame.primary),
            "terminal": bool(frame.terminal),
            "profile": profile_block,
            "slots": tray_messages.empty_slots(),
            "timing_ms": {},
            "analysis_ids": [],
        }

    supported_tokens = allowlist.supported_subset(profile_dins)
    if not supported_tokens:
        # Nothing on the list can be verified, so no photograph of anything
        # could succeed. Do NOT call the sidecar -- there is no ballot.
        frame = _frame_message(profile_dins, allowlist)
        return {
            "status": "unsupported_profile",
            "tray": False,
            "pipeline": None,
            "slot_count": tray_messages.SLOT_COUNT,
            "none_route": route,
            "message": tray_messages.msg_to_dict(frame.primary),
            "terminal": bool(frame.terminal),
            "profile": profile_block,
            "slots": tray_messages.empty_slots(),
            "timing_ms": {},
            "analysis_ids": [],
        }

    photo_bytes = await photo.read()
    brains_url = await resolve_brains_url()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0)) as http_client:
            response = await http_client.post(
                f"{brains_url}/tray/analyze",
                files={
                    "photo": (
                        photo.filename or "tray.jpg",
                        photo_bytes,
                        photo.content_type or "image/jpeg",
                    )
                },
                data={"profile_dins": json.dumps(supported_tokens), "match": "true"},
            )
    except httpx.HTTPError as exc:
        logger.warning("Brains sidecar unreachable at %s: %s", brains_url, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "BRAINS_UNAVAILABLE",
                    "message": "The brains sidecar service could not be reached. Make sure it is "
                    f"running at {brains_url}.",
                }
            },
        ) from exc

    try:
        body = response.json()
    except ValueError:
        body = {"detail": {"error": {"code": "BRAINS_INVALID_RESPONSE", "message": response.text}}}

    if response.status_code != 200:
        # Frame-level failure. The sidecar's envelope is already this app's
        # shape; pass it through with its own status code, exactly as the
        # single-pill route does.
        return JSONResponse(status_code=response.status_code, content=body)

    wells = body.get("wells") or []
    # ONE source for the hedge. The frozen match shape is exactly
    # {outcome, abstain_action, matched_din, breakdown} -- it carries no
    # disclaimer, so the "prefer the sidecar's own wording" branch that used to
    # sit here was unreachable in production and only ever ran under a mock
    # that had drifted from the contract. Two sources for one sentence is how
    # the two surfaces end up hedging differently.
    hedge = tray_messages.DEFAULT_HEDGE

    slots: list[dict[str, Any]] = []
    for well in wells[: tray_messages.SLOT_COUNT]:
        slots.append(
            tray_messages.slot_verdict(
                well,
                profile_dins=profile_dins,
                allowlist=allowlist,
                none_route=route,
                hedge=hedge,
                canonicalise_din=_sb2_token_to_canonical,
            )
        )
    # A short reply still renders a full grid: six cells, always, so the
    # patient can never be shown a tray with a slot silently missing.
    for filler in tray_messages.empty_slots()[len(slots):]:
        filler["pharmacist_hedge"] = hedge
        slots.append(filler)

    analysis_ids = await _persist_slots(db, current_user, photo.filename, body, slots)

    return {
        "status": "ok",
        "tray": bool(body.get("tray", True)),
        "pipeline": body.get("pipeline"),
        "slot_count": len(slots),
        "none_route": route,
        "message": None,
        "terminal": False,
        "profile": profile_block,
        "slots": slots,
        "timing_ms": body.get("timing_ms") or {},
        "analysis_ids": analysis_ids,
    }


async def _persist_slots(
    db: AsyncSession,
    current_user: User,
    photo_filename: str | None,
    body: dict[str, Any],
    slots: list[dict[str, Any]],
) -> list[str]:
    """One `Analysis` row per OCCUPIED slot -- N rows for N pills, following
    the single-pill route's field mapping exactly so Safety Records renders
    tray rows with no changes.

    Empty slots persist NOTHING: an empty well is not a scan, and six rows per
    photo would bury a three-pill tray's real results in its own history.

    The tray/slot linkage rides in the existing `label_info` JSON column
    rather than in new columns. This project is code-first with no migrations
    and `create_all` never ALTERs a live table -- a new column on the model
    that never reaches Postgres raises on every read and write while health
    checks stay green, which is exactly what took the site down on 2026-07-30.
    """
    tray_scan_id = str(uuid.uuid4())
    wells_by_index = {w.get("well"): w for w in (body.get("wells") or [])}
    rows: list[Analysis] = []
    for slot in slots:
        if not slot["occupied"]:
            continue
        record = (wells_by_index.get(slot["well"]) or {}).get("record") or {}
        breakdown = slot.get("breakdown") or None
        score = breakdown.get("S") if isinstance(breakdown, dict) else None
        shadow = record.get("shadow_fusion_suspected")
        if shadow is None:
            shadow = (record.get("diagnostics") or {}).get("shadow_fusion_suspected")
        # The decision of record is the SLOT VERDICT (post-D-7), never SB2's
        # raw decision -- `analyses.decision` is what Safety Records colours a
        # row from. See tray_messages.decision_of_record.
        decision, abstain_action = tray_messages.decision_of_record(slot)
        row = Analysis(
            user_id=current_user.id,
            status="completed",
            image_filename=photo_filename,
            pills_detected=[],
            label_info={
                "tray": True,
                "tray_scan_id": tray_scan_id,
                "slot": slot["slot"],
                "well": slot["well"],
                "verdict": slot["verdict"],
                "message_key": (slot["message"] or {}).get("key"),
                "pipeline": body.get("pipeline"),
                # AUDIT DETAIL ONLY. SB2's raw output, so the trail can show
                # what it concluded and that it ran at all. Nothing that maps a
                # row to a status or a colour may read these two keys.
                "sb2_decision": slot["decision"],
                "sb2_abstain_action": slot["abstain_action"],
            },
            guidance=None,
            safety_alerts=[],
            ml_pipeline_enabled=False,
            detected=bool(record.get("detected")) if record else False,
            decision=decision,
            abstain_action=abstain_action,
            matched_din=slot["matched_din"],
            top_candidate_score=float(score) if isinstance(score, (int, float)) else None,
            top_candidate_breakdown=breakdown,
            shadow_fusion_suspected=shadow,
        )
        db.add(row)
        rows.append(row)
    # ids are only readable AFTER the flush -- `Analysis.id` is a column
    # default, not a Python-side attribute default.
    await db.flush()
    return [r.id for r in rows]
