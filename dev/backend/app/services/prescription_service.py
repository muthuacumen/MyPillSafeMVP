from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.prescription import Prescription
from app.schemas.prescription import PrescriptionUpdate

#: Fields the generic setattr loop must never touch -- each has its own
#: handling below (`din` implies `din_confirmed`; `review_status` is gated by
#: the guardrail approval rules in the route; `confirmed_flags` is a
#: request-only acknowledgement, not a column).
_MANUAL_FIELDS = {"din", "review_status", "confirmed_flags"}


async def list_active_for_patient(
    db: AsyncSession,
    patient_id: str,
    *,
    review_status: str | None = None,
) -> list[Prescription]:
    """Active prescriptions for a patient.

    `review_status='approved'` is what every SCHEDULE-bearing surface asks
    for (dashboard schedule, the dose-reminder engine, and the pill-scan
    profile below) -- a proposal that the patient has not approved must
    never generate a reminder (non-negotiable §0.1). The unfiltered call is
    what My Medications uses, because that screen is where the pending
    proposals get reviewed.
    """
    query = select(Prescription).where(
        Prescription.patient_id == patient_id, Prescription.is_active == True  # noqa: E712
    )
    if review_status:
        query = query.where(Prescription.review_status == review_status)
    result = await db.execute(query.order_by(Prescription.created_at.desc()))
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
    pill_verifiable: bool | None = None,
    approve: bool = False,
) -> Prescription:
    """`din_provided`/`normalized_din` are computed by the route (format
    validation is an HTTP concern) -- `normalized_din` is already the
    canonical 8-digit form, or `None` when the caller sent `din: null` to
    explicitly clear it. Handled separately from the generic field loop
    because `din` implies also setting/clearing `din_confirmed`.

    `approve` is likewise decided by the route, which is the only place that
    can check the guardrail flags against what the user acknowledged. An
    edit WITHOUT approve leaves `review_status` untouched, so touching a
    pending medication can never silently promote it (§0.1).
    """
    for field, value in payload.model_dump(exclude_none=True, exclude=_MANUAL_FIELDS).items():
        setattr(prescription, field, value)
    if din_provided:
        prescription.din = normalized_din
        prescription.din_confirmed = normalized_din is not None
        # Task B3: resolved by the route at confirm time; None when the DIN
        # was cleared OR when the sidecar could not tell us -- either way the
        # UI shows no badge rather than an invented one.
        prescription.pill_verifiable = pill_verifiable if normalized_din is not None else None
    if approve:
        prescription.review_status = "approved"
    await db.flush()
    await db.refresh(prescription)
    return prescription


async def soft_delete(db: AsyncSession, prescription: Prescription) -> None:
    prescription.is_active = False
    await db.flush()
