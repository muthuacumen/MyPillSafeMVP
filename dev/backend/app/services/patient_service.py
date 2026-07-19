from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.patient import Patient
from app.schemas.patient import PatientUpdate


async def get_patient_by_user_id(db: AsyncSession, user_id: str) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    return result.scalar_one_or_none()


async def update_patient(db: AsyncSession, patient: Patient, payload: PatientUpdate) -> Patient:
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    await db.flush()
    await db.refresh(patient)
    return patient
