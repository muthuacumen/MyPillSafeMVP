"""Safety Records — read-only view over past scans (Priority 3 /dashboard/safety).

Derives data from the existing `analyses` table, written by both the legacy
`/analyze` demo stub and (Phase 3) `/analyze/pill/v2`'s real IMB1+SB2 scans.
For pill-v2 rows, `match_status` is SB2's own decision, verbatim -- never
reinterpreted (verify -> matched/green, reject -> unmatched/red, abstain ->
warning/amber). No new write path here — this endpoint only reads.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.scan import ScanRecord
from app.services import prescription_service
from app.services.patient_service import get_patient_by_user_id

router = APIRouter(prefix="/scans", tags=["scans"])

# SB2's decision vocabulary mapped onto this endpoint's pre-existing 3-state
# match_status (matched=green, unmatched=red, warning=amber) -- abstain maps
# to "warning", never "unmatched"; the three decisions stay distinguishable
# via the dedicated `decision` field below regardless of this mapping.
_DECISION_TO_MATCH_STATUS = {"verify": "matched", "reject": "unmatched", "abstain": "warning"}


@router.get("/me", response_model=list[ScanRecord])
async def list_my_scans(
    current_user: Annotated[User, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[ScanRecord]:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
    )
    analyses = list(result.scalars().all())

    active_drug_names: set[str] = set()
    patient = await get_patient_by_user_id(db, current_user.id)
    if patient:
        prescriptions = await prescription_service.list_active_for_patient(db, patient.id)
        active_drug_names = {p.drug_name.strip().casefold() for p in prescriptions}

    records: list[ScanRecord] = []
    for row in analyses:
        drug_name = (row.label_info or {}).get("drug_name")
        # Pill-v2 verify rows never populate label_info (that's the legacy
        # /analyze demo-stub's field) -- their product identity lives in
        # matched_din, already persisted on the scan row (routes/pill.py).
        # The product NAME isn't persisted (only the score/breakdown are),
        # so fall back to showing the DIN itself rather than "Unknown".
        if not drug_name and row.decision == "verify" and row.matched_din:
            drug_name = f"DIN {row.matched_din}"
        is_pill_v2_row = row.decision is not None or row.detected is not None

        if row.decision is not None:
            match_status = _DECISION_TO_MATCH_STATUS.get(row.decision, "unmatched")
            action_taken = f"Pill scan — {row.decision}"
            if row.abstain_action:
                action_taken += f" ({row.abstain_action})"
        elif is_pill_v2_row:
            # Pill-v2 scan where no pill was detected in the photo at all.
            match_status = "unmatched"
            action_taken = "Pill scan — no pill detected"
        elif row.safety_alerts:
            match_status = "warning"
            action_taken = "Guidance shown" if row.guidance else "Logged"
        elif drug_name and drug_name.strip().casefold() in active_drug_names:
            match_status = "matched"
            action_taken = "Guidance shown" if row.guidance else "Logged"
        else:
            match_status = "unmatched"
            action_taken = "Guidance shown" if row.guidance else "Logged"

        records.append(
            ScanRecord(
                id=row.id,
                created_at=row.created_at,
                drug_name=drug_name,
                match_status=match_status,
                action_taken=action_taken,
                image_filename=row.image_filename,
                detected=row.detected,
                decision=row.decision,
                abstain_action=row.abstain_action,
                matched_din=row.matched_din,
                top_candidate_score=row.top_candidate_score,
                shadow_fusion_suspected=row.shadow_fusion_suspected,
            )
        )
    return records
