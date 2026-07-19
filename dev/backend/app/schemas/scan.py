from datetime import datetime
from pydantic import BaseModel


class ScanRecord(BaseModel):
    id: str
    created_at: datetime
    drug_name: str | None
    match_status: str  # matched | unmatched | warning
    action_taken: str
    image_filename: str | None

    # --- Phase 3 (pill-scan v2 / IMB1+SB2) -- populated only for scans that
    # went through `/analyze/pill/v2`; null for the pre-existing demo-stub
    # `/analyze` rows. `decision`/`abstain_action` are SB2's own vocabulary,
    # surfaced verbatim (never reinterpreted -- see SB2 CONTRACT.md).
    detected: bool | None = None
    decision: str | None = None
    abstain_action: str | None = None
    matched_din: str | None = None
    top_candidate_score: float | None = None
    shadow_fusion_suspected: bool | None = None
