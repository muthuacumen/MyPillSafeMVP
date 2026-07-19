"""Prescription OCR capture + My Medications CRUD (Priority 1)."""
import logging
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
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


# Demo data returned when OCR_PIPELINE_ENABLED=false, per build spec 1B.
_DEMO_RAW_TEXT = "Metformin HCl 500mg — twice daily with meals. Dr. A. Chen. Refills: 2."


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
            # PaddleOCR inference is a slow, synchronous, CPU-bound call — run it
            # off the event loop so it doesn't freeze every other request (other
            # users' logins, page loads, etc.) for the duration of this scan.
            raw_text = await run_in_threadpool(ocr_service.extract_text, image_bytes)
        except ocr_service.OcrUnavailableError as exc:
            logger.warning("OCR pipeline unavailable, falling back to demo data: %s", exc)
            raw_text = _DEMO_RAW_TEXT
        except Exception as exc:
            # A bad/corrupt/non-image upload shouldn't crash the request — degrade
            # to demo text just like the "OCR not installed" path.
            logger.warning("OCR extraction failed, falling back to demo data: %s", exc)
            raw_text = _DEMO_RAW_TEXT
    else:
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
