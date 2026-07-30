"""Prescription OCR capture + My Medications CRUD (Priority 1).

Task A2.2 (deploy-readiness build) removed the old behaviour where ANY OCR
failure -- sidecar down, timeout, corrupt image -- silently fell back to
`_DEMO_RAW_TEXT`, a canned "Metformin HCl 500mg..." string. In a medication-
safety app, silently inventing a prescription from a failed scan is the
worst available failure mode: it directly contradicts this project's
abstain-over-guess principle, and once OCR became a remote call to the
brains sidecar (Task A1), that fallback became reachable in ordinary
operation (a closed laptop, a slow network), not just a missing local
dependency. Real OCR failure now raises a clean, honest 503 instead. The
demo text survives ONLY behind `OCR_PIPELINE_ENABLED=false`, an explicit
local-dev opt-out that must never be set in production (see that flag's
comment in `.env.example`).
"""
import hashlib
import logging
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import DinSuggestion, PrescriptionOut, PrescriptionUpdate, PrescriptionWithSuggestions
from app.services import (
    brains_client,
    din_utils,
    lasa,
    ocr_service,
    prescription_parser,
    prescription_service,
    rx_extract_service,
    rx_guardrails,
)
from app.services.patient_service import get_patient_by_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

_404 = {"error": {"code": "NOT_FOUND", "message": "Prescription not found."}}
_NO_PROFILE = {"error": {"code": "NOT_FOUND", "message": "Patient profile not found."}}


async def _get_patient_or_404(db: AsyncSession, user: User):
    patient = await get_patient_by_user_id(db, user.id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)
    return patient


# Demo data returned ONLY when OCR_PIPELINE_ENABLED=false -- an explicit
# local-dev opt-out switch (per build spec 1B) that fabricates prescription
# text regardless of the uploaded image. Must NEVER be set false in
# production: a real OCR failure must surface as OCR_UNAVAILABLE (503), not
# silently substitute this text (Task A2.2 -- see module docstring).
_DEMO_RAW_TEXT = "Metformin HCl 500mg — twice daily with meals. Dr. A. Chen. Refills: 2."

_OCR_UNAVAILABLE_MESSAGE = "Prescription scanning is temporarily unavailable. Please try again shortly."

_REVIEW_STATUSES = {"pending", "approved"}


async def _propose_medications(raw_text: str) -> tuple[list[rx_guardrails.MedicationProposal], str]:
    """Produce guarded medication PROPOSALS from raw label text.

    Returns `(proposals, parse_source)`. The proposer is swappable
    (`RX_PARSE_BACKEND`) and skippable (`RX_LLM_PARSE_ENABLED`), and falls
    back to the deterministic regex parser on ANY sidecar/Ollama failure --
    but every path lands in the same `rx_guardrails.apply`, so the safety
    layer is identical regardless of who proposed. That is the whole point
    of the redesign: the model is an opinion, the guards are the contract.
    """
    use_llm = settings.RX_LLM_PARSE_ENABLED and settings.RX_PARSE_BACKEND.lower() == "qwen"
    if use_llm:
        try:
            payload = await rx_extract_service.extract_medications(raw_text)
        except rx_extract_service.RxExtractUnavailableError as exc:
            logger.warning("Rx LLM extraction unavailable, falling back to regex: %s", exc)
        else:
            proposals = [rx_guardrails.from_llm_medication(item) for item in payload["medications"]]
            if proposals:
                return rx_guardrails.apply(proposals, raw_text), "qwen"
            # An empty list is a legitimate answer ("no medications on this
            # label"), but the regex parser always returns at least one
            # record and the user is better served by something to correct
            # than by an empty screen. Fall through, and say so honestly in
            # `parse_source`.
            logger.info("Rx LLM extraction returned no medications; using regex proposer instead")

    parsed = prescription_parser.parse_medications(raw_text)
    proposals = [rx_guardrails.from_parsed_medication(med) for med in parsed]
    return rx_guardrails.apply(proposals, raw_text), "regex"


@router.post("", response_model=list[PrescriptionWithSuggestions], status_code=status.HTTP_201_CREATED)
async def upload_prescription(
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    image: UploadFile = File(...),
) -> list[PrescriptionWithSuggestions]:
    patient = await _get_patient_or_404(db, current_user)

    image_bytes = await image.read()
    upload_subdir = os.path.join(settings.UPLOAD_DIR, "prescriptions", patient.id)
    os.makedirs(upload_subdir, exist_ok=True)
    ext = os.path.splitext(image.filename or "")[1] or ".jpg"
    saved_name = f"{uuid.uuid4()}{ext}"
    saved_path = os.path.join(upload_subdir, saved_name)
    with open(saved_path, "wb") as fh:
        fh.write(image_bytes)

    if settings.OCR_PIPELINE_ENABLED:
        try:
            # The sidecar call is itself async (httpx) and already runs off
            # any CPU-bound work in-process -- the actual OCR inference now
            # happens on the remote sidecar's subprocess, not here.
            raw_text = await ocr_service.extract_text(
                image_bytes, image.filename or "prescription.jpg", image.content_type or "image/jpeg"
            )
        except ocr_service.OcrUnavailableError as exc:
            # Honest failure, not a fabricated prescription (see module
            # docstring). Log the real cause (including the sidecar URL)
            # server-side only -- the user-facing message stays generic.
            logger.warning("OCR pipeline unavailable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": {"code": "OCR_UNAVAILABLE", "message": _OCR_UNAVAILABLE_MESSAGE}},
            ) from exc
    else:
        # Explicit local-dev opt-out only -- see _DEMO_RAW_TEXT's comment.
        raw_text = _DEMO_RAW_TEXT

    # FixbySonnet1 Task 1d (permanent anomaly attribution): one INFO log
    # line per scan tying the received image (hash + length) to the saved
    # file and the OCR text it produced, so a future "OCR text matches
    # nothing that was uploaded" anomaly is diagnosable from a single log
    # read instead of requiring a live investigation. No image content is
    # logged -- only its sha256 prefix and byte length.
    image_sha256_prefix = hashlib.sha256(image_bytes).hexdigest()[:12]
    raw_text_lines = raw_text.count("\n") + (1 if raw_text else 0)
    logger.info(
        "Prescription OCR scan: image_sha256=%s image_bytes=%d saved_path=%s "
        "raw_text_lines=%d raw_text_head=%r",
        image_sha256_prefix, len(image_bytes), saved_path, raw_text_lines, raw_text[:200],
    )

    # Proposer (qwen sidecar, or regex on failure/kill-switch) -> guardrails
    # -> server-side time derivation. See `_propose_medications`.
    medications, parse_source = await _propose_medications(raw_text)

    # DIN linking (Phase 2, SB2 CONTRACT §2): propose candidates for each
    # parsed medication from the sidecar's reference table, but never
    # auto-commit -- the patient confirms via PATCH. Failure-tolerant by
    # construction (brains_client.search_reference never raises), so a
    # down/slow sidecar degrades to an empty suggestion list, never blocks
    # the save. The same lookup doubles as guardrail G1's catalog
    # cross-check, so a not-found medication is flagged rather than
    # silently accepted -- one round of calls, not two.
    suggestions_per_med: list[list[dict]] = []
    for med in medications:
        # The dosage is NOT concatenated into the query any more: the drug
        # name already carries the strength on most labels, and appending it
        # again diluted the real name token badly enough that unrelated
        # products won (see `brains_client.clean_search_query`). It is passed
        # as a ranking hint instead, which surfaces the label's own strength
        # among otherwise score-tied variants.
        suggestions = await brains_client.search_reference(
            med.drug_name, limit=5, strength_hint=med.dosage
        )
        # LASA annotation before the candidates are handed to the UI: when no
        # candidate keeps every word the label printed, the review card must
        # not offer any of them as a one-tap confirm (app/services/lasa.py).
        # Measured against the parsed name, which is what the search used.
        lasa.annotate_suggestions(med.drug_name, suggestions)
        rx_guardrails.flag_not_in_reference(med, suggestions)
        suggestions_per_med.append(suggestions)

    records = [
        Prescription(
            patient_id=patient.id,
            drug_name=med.drug_name,
            dosage=med.dosage,
            frequency_text=med.frequency_text,
            frequency_type=med.frequency_type,
            time_slots=med.time_slots,
            specific_times=med.specific_times,
            with_food=med.with_food,
            purpose=med.purpose,
            max_daily_dose=med.max_daily_dose,
            image_path=saved_path,
            # PROPOSAL, not a medication: no reminder fires and no DIN is
            # linked until the patient approves it (non-negotiable §0.1).
            review_status="pending",
            parse_source=parse_source,
            parse_flags=",".join(med.flags)[:255] or None,
        )
        for med in medications
    ]
    db.add_all(records)
    await db.flush()

    # Permanent parse-attribution log line, same idiom as the Task-1d OCR
    # anomaly log above: which proposer spoke, what the guards flagged, and
    # how long it took, per scan -- so a "why did it schedule that?" question
    # is answerable from a log read instead of a live re-investigation.
    logger.info(
        "Prescription parse: image_sha256=%s parse_source=%s medications=%d flags=%s",
        image_sha256_prefix, parse_source, len(medications),
        [",".join(med.flags) or "-" for med in medications],
    )

    results: list[PrescriptionWithSuggestions] = []
    for record, suggestions in zip(records, suggestions_per_med):
        results.append(
            PrescriptionWithSuggestions.model_validate(record).model_copy(
                update={"din_suggestions": [DinSuggestion.model_validate(s) for s in suggestions]}
            )
        )
    return results


@router.get("/me", response_model=list[PrescriptionOut])
async def list_my_prescriptions(
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    review_status: Annotated[str | None, Query(pattern="^(pending|approved)$")] = None,
) -> list[Prescription]:
    """Unfiltered by default (My Medications needs the pending proposals in
    order to review them). Schedule-bearing callers -- the dashboard's
    today's-doses list and the dose-reminder engine -- pass
    `review_status=approved`, so an unapproved proposal can never produce a
    reminder (non-negotiable §0.1)."""
    patient = await _get_patient_or_404(db, current_user)
    return await prescription_service.list_active_for_patient(
        db, patient.id, review_status=review_status
    )


@router.get("/{prescription_id}/image")
async def get_prescription_image(
    prescription_id: str,
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    patient = await _get_patient_or_404(db, current_user)
    prescription = await prescription_service.get_owned(db, prescription_id, patient.id)
    if not prescription or not prescription.image_path or not os.path.exists(prescription.image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    return FileResponse(prescription.image_path)


@router.patch("/{prescription_id}", response_model=PrescriptionOut)
async def update_prescription(
    prescription_id: str,
    payload: PrescriptionUpdate,
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Prescription:
    patient = await _get_patient_or_404(db, current_user)
    prescription = await prescription_service.get_owned(db, prescription_id, patient.id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)

    # Tri-state DIN handling: omitted (not in model_fields_set) -> leave
    # untouched; a string -> validate/normalize to canonical 8-digit and
    # confirm; explicit `null` -> unset both `din` and `din_confirmed`.
    din_provided = "din" in payload.model_fields_set
    normalized_din: str | None = None
    pill_verifiable: bool | None = None
    if din_provided and payload.din is not None:
        try:
            normalized_din = din_utils.normalize_din(payload.din)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "INVALID_DIN", "message": str(exc)}},
            ) from exc
        # Task B3: is this DIN photo-checkable? Resolved once, here, because
        # DIN confirm is a rare user action -- unlike the list read, which
        # the dose-reminder engine polls every 30 s.
        #
        # `get_profile_rows` returns None (not {}) when the sidecar could not
        # answer, and that stays NULL rather than becoming `false`. A wrong
        # "this can't be checked by photo" badge would teach a user not to
        # bother verifying a pill they actually could have verified -- the
        # expensive direction of this error.
        token = din_utils.to_sb2_token(normalized_din)
        profile_rows = await brains_client.get_profile_rows([token])
        if profile_rows is not None and token in profile_rows:
            pill_verifiable = bool(profile_rows[token].get("pill_verifiable"))

    # --- Review approval gate (FixbyOPUS3 Task A3) -------------------------
    # `review_status` is write-once-forward: only 'approved' is accepted, and
    # only when every BLOCKING guardrail flag on this medication has been
    # either resolved by the resulting state or explicitly acknowledged by
    # the user. Editing any other field leaves the status untouched, so
    # correcting a pending proposal never silently promotes it.
    approve = False
    if payload.review_status is not None:
        if payload.review_status not in _REVIEW_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "INVALID_REVIEW_STATUS",
                        "message": f"review_status must be one of {sorted(_REVIEW_STATUSES)}.",
                    }
                },
            )
        approve = payload.review_status == "approved"

    if approve:
        resulting_times = (
            payload.specific_times
            if payload.specific_times is not None
            else list(prescription.specific_times or [])
        )
        unresolved = rx_guardrails.unresolved_blocking_flags(
            (prescription.parse_flags or "").split(",") if prescription.parse_flags else [],
            specific_times=resulting_times,
            confirmed_flags=payload.confirmed_flags,
        )
        if unresolved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "REVIEW_INCOMPLETE",
                        "message": (
                            "This medication still needs your attention before it can be "
                            f"approved: {', '.join(unresolved)}."
                        ),
                        "unresolved_flags": unresolved,
                    }
                },
            )

    return await prescription_service.update_prescription(
        db, prescription, payload,
        din_provided=din_provided, normalized_din=normalized_din,
        pill_verifiable=pill_verifiable, approve=approve,
    )


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(
    prescription_id: str,
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    patient = await _get_patient_or_404(db, current_user)
    prescription = await prescription_service.get_owned(db, prescription_id, patient.id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    await prescription_service.soft_delete(db, prescription)
