"""Analyze endpoint — pill/label image analysis (ML stub for Sprint 4)."""
import uuid
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.models.patient import Patient

router = APIRouter(prefix="/analyze", tags=["analyze"])


class PillInfo(BaseModel):
    pill_id: str
    name: str
    confidence: float
    color: str
    shape: str
    imprint: str | None


class LabelInfo(BaseModel):
    drug_name: str | None
    dosage: str | None
    frequency: str | None
    refills_remaining: int | None
    expiry_date: str | None


class AnalyzeResponse(BaseModel):
    request_id: str
    status: str
    pills_detected: list[PillInfo]
    label: LabelInfo
    guidance: str
    safety_alerts: list[str]
    ml_pipeline_enabled: bool


class AnalysisHistoryItem(BaseModel):
    id: str
    status: str
    image_filename: str | None
    guidance: str | None
    safety_alerts: list[str]
    ml_pipeline_enabled: bool
    created_at: datetime


@router.post("", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_medication(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    image: UploadFile = File(...),
) -> AnalyzeResponse:
    if not settings.ML_PIPELINE_ENABLED:
        pill = PillInfo(
            pill_id="STUB-001",
            name="Metformin 500mg (demo)",
            confidence=0.97,
            color="white",
            shape="oval",
            imprint="M500",
        )
        label = LabelInfo(
            drug_name="Metformin HCl",
            dosage="500 mg",
            frequency="twice daily with meals",
            refills_remaining=2,
            expiry_date="2026-12",
        )
        guidance = (
            "Metformin is commonly prescribed for type 2 diabetes. "
            "Take with food to reduce stomach upset. This tool provides "
            "decision support only — always confirm with your pharmacist."
        )
        safety_alerts: list[str] = []

        # Persist analysis record
        record = Analysis(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            status="completed",
            image_filename=image.filename,
            pills_detected=[p.model_dump() for p in [pill]],
            label_info=label.model_dump(),
            guidance=guidance,
            safety_alerts=safety_alerts,
            ml_pipeline_enabled=False,
        )
        db.add(record)

        # Update patient stats
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            patient.medications_analyzed += 1
            patient.last_scan_at = datetime.utcnow()

        await db.flush()

        return AnalyzeResponse(
            request_id=record.id,
            status="stub",
            pills_detected=[pill],
            label=label,
            guidance=guidance,
            safety_alerts=safety_alerts,
            ml_pipeline_enabled=False,
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": {"code": "NOT_IMPLEMENTED", "message": "ML pipeline not yet configured."}},
    )


@router.get("/history", response_model=list[AnalysisHistoryItem])
async def get_my_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
) -> list[AnalysisHistoryItem]:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        AnalysisHistoryItem(
            id=r.id,
            status=r.status,
            image_filename=r.image_filename,
            guidance=r.guidance,
            safety_alerts=r.safety_alerts or [],
            ml_pipeline_enabled=r.ml_pipeline_enabled,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{analysis_id}", response_model=AnalysisHistoryItem)
async def get_analysis(
    analysis_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisHistoryItem:
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Analysis not found."}},
        )
    return AnalysisHistoryItem(
        id=row.id,
        status=row.status,
        image_filename=row.image_filename,
        guidance=row.guidance,
        safety_alerts=row.safety_alerts or [],
        ml_pipeline_enabled=row.ml_pipeline_enabled,
        created_at=row.created_at,
    )
