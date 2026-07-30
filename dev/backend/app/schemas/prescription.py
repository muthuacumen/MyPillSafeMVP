from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    #: Task B3: True/False once a DIN is confirmed, `null` when it could not
    #: be established (sidecar down) -- the UI renders no badge for `null`.
    pill_verifiable: bool | None = None
    created_at: datetime
    updated_at: datetime

    # --- Review workflow (FixbyOPUS3 Task A3) -------------------------------
    #: 'pending' until the patient approves it in the review screen.
    review_status: str = "pending"
    #: Which proposer produced this row -- 'qwen' or 'regex'.
    parse_source: str | None = None
    #: Guardrail flags, exposed as a list even though the column stores a
    #: comma-separated string (String(255) -- no JSON column needed for a
    #: handful of short, fixed tokens).
    parse_flags: list[str] = Field(default_factory=list)

    @field_validator("parse_flags", mode="before")
    @classmethod
    def _split_flags(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [flag for flag in value.split(",") if flag]
        return value


class DinSuggestion(BaseModel):
    """One candidate row from the brains sidecar's /reference/search, DIN
    already normalized to the app's canonical 8-digit form (see
    app/services/din_utils.py)."""

    din: str
    product: str
    strength: str | None
    score: float
    # Task B2 (two-tier reference): is this DIN in the 7,055-DIN appearance
    # tier as well as the 11,609-DIN profile tier -- i.e. can a photo ever
    # verify it? `None` = the sidecar did not say (unknown), which must not
    # render as "cannot be checked".
    pill_verifiable: bool | None = None
    # LASA look-alike detection (2026-07-30, app/services/lasa.py).
    # `name_match` is "exact" when this candidate's name contains every word
    # the label printed, "manufacturer" when only a generic-manufacturer
    # prefix differs, and "look_alike" when it has dropped a real word from
    # the label -- the ZOLTIRAX->ZOVIRAX / TYLENOL PM->TYLENOL EXTRA STRENGTH
    # state that no score cutoff can separate. Defaults keep older clients
    # and any caller that does not annotate working unchanged.
    name_match: str = "exact"
    missing_tokens: list[str] = Field(default_factory=list)


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

    # --- Review workflow (FixbyOPUS3 Task A3) -------------------------------
    #: Only 'approved' is accepted from a client (there is no un-approving
    #: back to 'pending' -- the medication is already live at that point and
    #: the user's tool for retracting it is delete). Any OTHER edit leaves
    #: the status exactly as it was, so editing a pending medication never
    #: accidentally promotes it.
    review_status: str | None = None
    #: Guardrail flags the user has explicitly acknowledged in the review
    #: screen ("I checked this against my label"). Required to approve a
    #: medication carrying a blocking flag -- see
    #: `rx_guardrails.unresolved_blocking_flags`.
    confirmed_flags: list[str] | None = None
