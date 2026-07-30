import uuid
from datetime import date, datetime
from sqlalchemy import String, Boolean, Date, DateTime, Integer, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    time_slots: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    specific_times: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    with_food: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_daily_dose: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prescribing_doctor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refills_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Canonical 8-digit zero-padded Health Canada DIN (e.g. "00013803"), never
    # the SB2 sidecar's token form ("DIN13803") -- see app/services/din_utils.py
    # for the shared conversion helpers used at the sidecar boundary.
    din: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    din_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # FixbyOPUS3 Task B3. Whether the confirmed DIN is in the APPEARANCE tier
    # (7,055 DINs with harmonized colour/shape/imprint) as opposed to only the
    # PROFILE tier (11,609 marketed human DINs). False means a real medication
    # that a photo simply cannot check -- an insulin pen, inhaler, cream, drop
    # or patch.
    #
    # Resolved ONCE, at DIN-confirm time (a rare, user-initiated action),
    # rather than on every list read: the dose-reminder engine polls
    # /prescriptions/me every 30 s and must not drag a sidecar call along.
    # NULL means "not established" (e.g. the sidecar was down at confirm
    # time) and renders NO badge -- silence, not a guess.
    pill_verifiable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # --- Review workflow (FixbyOPUS3 Task A3) -------------------------------
    # Nothing auto-commits a drug name, DIN or schedule (non-negotiable §0.1):
    # every parsed medication lands as a PROPOSAL and only becomes a real,
    # reminder-generating medication once the patient approves it.
    #
    # Rows that predate this column grandfather to 'approved' -- they were
    # created before the review screen existed, are already visible in the
    # user's list, and silently demoting them to 'pending' would switch off
    # a working senior's reminders overnight. The backfill happens once, in
    # the boot-time column sync (app/core/database.py).
    review_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    #: Which proposer produced this row: 'qwen' (sidecar LLM) or 'regex'.
    parse_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    #: Comma-separated guardrail flags, e.g. "not_on_label,needs_schedule".
    parse_flags: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="prescriptions")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Prescription id={self.id} drug={self.drug_name}>"
