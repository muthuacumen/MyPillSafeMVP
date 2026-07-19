"""Request schema for `POST /api/v1/qa/chat` (Phase 4 -- BB3 Q&A + CB4
voice). The response shape varies by BB3 status (8 frozen values, see
BB3/CONTRACT.md §2, plus this app's `guard_refused`/`context_ready`
extensions) so routes/qa.py returns plain dicts rather than a single
response_model, matching routes/pill.py's existing idiom for the same
reason (heterogeneous sidecar passthrough shapes)."""
from pydantic import BaseModel


class QAChatRequest(BaseModel):
    message: str
    # Canonical 8-digit DIN bypass (SB2/BB3's app-supplied "safest calling
    # pattern" -- e.g. a confirmed medication card's DIN, or a just-verified
    # pill scan's matched_din). Converted to the sidecar's token form at the
    # boundary via app/services/din_utils.py, exactly like routes/pill.py.
    din: str | None = None
    # Pass on the turn AFTER a status="confirm" response, once the user has
    # tapped "Yes, I meant X" -- never auto-passed (BB3 CONTRACT.md §1: "Do
    # not auto-pass it without an explicit user confirmation").
    confirmed_name: str | None = None
    language: str = "English"
