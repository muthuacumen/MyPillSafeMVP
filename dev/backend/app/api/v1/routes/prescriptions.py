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
import logging
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import DinSuggestion, PrescriptionOut, PrescriptionUpdate, PrescriptionWithSuggestions
from app.services import brains_client, din_utils, ocr_service, prescription_parser, prescription_service
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

    medications = prescription_parser.parse_medications(raw_text)
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
        )
        for med in medications
    ]
    db.add_all(records)
    await db.flush()

    # DIN linking (Phase 2, SB2 CONTRACT §2): propose candidates for each
    # parsed medication from the sidecar's reference table, but never
    # auto-commit -- the patient confirms via PATCH. Failure-tolerant by
    # construction (brains_client.search_reference never raises), so a
    # down/slow sidecar degrades to an empty suggestion list, never blocks
    # the save.
    results: list[PrescriptionWithSuggestions] = []
    for record, med in zip(records, medications):
        query = f"{med.drug_name} {med.dosage}".strip() if med.dosage else med.drug_name
        suggestions = await brains_client.search_reference(query, limit=5)
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
) -> list[Prescription]:
    patient = await _get_patient_or_404(db, current_user)
    return await prescription_service.list_active_for_patient(db, patient.id)


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
    if din_provided and payload.din is not None:
        try:
            normalized_din = din_utils.normalize_din(payload.din)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "INVALID_DIN", "message": str(exc)}},
            ) from exc

    return await prescription_service.update_prescription(
        db, prescription, payload, din_provided=din_provided, normalized_din=normalized_din
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
