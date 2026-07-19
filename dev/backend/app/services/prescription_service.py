from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.prescription import Prescription
from app.schemas.prescription import PrescriptionUpdate


async def list_active_for_patient(db: AsyncSession, patient_id: str) -> list[Prescription]:
    result = await db.execute(
        select(Prescription)
        .where(Prescription.patient_id == patient_id, Prescription.is_active == True)
        .order_by(Prescription.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, prescription_id: str, patient_id: str) -> Prescription | None:
    result = await db.execute(
        select(Prescription).where(
            Prescription.id == prescription_id,
            Prescription.patient_id == patient_id,
        )
    )
    return result.scalar_one_or_none()


async def update_prescription(
    db: AsyncSession,
    prescription: Prescription,
    payload: PrescriptionUpdate,
    *,
    din_provided: bool = False,
    normalized_din: str | None = None,
) -> Prescription:
    """`din_provided`/`normalized_din` are computed by the route (format
    validation is an HTTP concern) -- `normalized_din` is already the
    canonical 8-digit form, or `None` when the caller sent `din: null` to
    explicitly clear it. Handled separately from the generic field loop
    because `din` implies also setting/clearing `din_confirmed`."""
    for field, value in payload.model_dump(exclude_none=True, exclude={"din"}).items():
        setattr(prescription, field, value)
    if din_provided:
        prescription.din = normalized_din
        prescription.din_confirmed = normalized_din is not None
    await db.flush()
    await db.refresh(prescription)
    return prescription


async def soft_delete(db: AsyncSession, prescription: Prescription) -> None:
    prescription.is_active = False
    await db.flush()
