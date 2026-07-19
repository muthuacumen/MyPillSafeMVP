from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    drug_name: str
    dosage: str | None
    frequency_text: str | None
    frequency_type: str | None
    time_slots: list[str]
    specific_times: list[str]
    with_food: bool
    purpose: str | None
    max_daily_dose: int | None
    prescribing_doctor: str | None
    refills_remaining: int | None
    expiry_date: date | None
    is_active: bool
    image_path: str | None
    din: str | None
    din_confirmed: bool
    created_at: datetime
    updated_at: datetime


class DinSuggestion(BaseModel):
    """One candidate row from the brains sidecar's /reference/search, DIN
    already normalized to the app's canonical 8-digit form (see
    app/services/din_utils.py)."""

    din: str
    product: str
    strength: str | None
    score: float


class PrescriptionWithSuggestions(PrescriptionOut):
    """Response shape for `POST /prescriptions` only -- adds the sidecar's
    top DIN candidates for the patient's one-tap confirm step. Never
    auto-committed; `din`/`din_confirmed` above stay unset until the patient
    confirms via `PATCH`."""

    din_suggestions: list[DinSuggestion] = Field(default_factory=list)


class PrescriptionUpdate(BaseModel):
    drug_name: str | None = None
    dosage: str | None = None
    frequency_text: str | None = None
    frequency_type: str | None = None
    time_slots: list[str] | None = None
    specific_times: list[str] | None = None
    with_food: bool | None = None
    purpose: str | None = None
    max_daily_dose: int | None = None
    prescribing_doctor: str | None = None
    refills_remaining: int | None = None
    expiry_date: date | None = None
    is_active: bool | None = None
    # Tri-state: omitted -> leave untouched; a string -> validate/normalize
    # and set din_confirmed=True; explicit `null` -> clear both `din` and
    # `din_confirmed`. See routes/prescriptions.py (checks
    # `"din" in payload.model_fields_set` to tell "omitted" from "null").
    din: str | None = None
