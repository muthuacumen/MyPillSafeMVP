"""Thin authenticated proxy to the brains sidecar's `GET /reference/search`
(Phase 2 of the app x brains integration).

The frontend never calls the sidecar directly -- this route exists purely
so the "pick a different one" / edit-medication DIN search box has an
authenticated, same-origin endpoint to call. See
`documentation/integration/INTEGRATION_PLAN.md` Phase 2 and
`app/services/brains_client.py`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_patient
from app.models.user import User
from app.schemas.prescription import DinSuggestion
from app.services import brains_client

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/search", response_model=list[DinSuggestion])
async def search_reference(
    _: Annotated[User, Depends(get_current_patient)],
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=25),
) -> list[dict]:
    """Fuzzy product-name search over the SB2 reference table, DIN tokens
    already converted to the app's canonical 8-digit form.

    Failure-tolerant like the underlying sidecar call: a down/slow sidecar
    yields an empty list (HTTP 200), never an error -- DIN search is a
    convenience, not a hard dependency.
    """
    return await brains_client.search_reference(q, limit=limit)
