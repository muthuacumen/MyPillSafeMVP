"""Admin-only endpoints — requires ADMIN role on the JWT."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import (
    AnalysisSummary,
    BrainsPinRequest,
    BrainsPoolEntry,
    PlatformStats,
    RoleUpdate,
    UserListItem,
)
from app.services import brains_registry
from app.services.admin_service import (
    delete_user,
    get_platform_stats,
    get_user_by_id_admin,
    list_all_analyses,
    list_users,
    set_user_active,
    update_user_role,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_404 = {"error": {"code": "NOT_FOUND", "message": "User not found."}}


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=PlatformStats)
async def admin_stats(
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformStats:
    return PlatformStats(**(await get_platform_stats(db)))


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserListItem])
async def admin_list_users(
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
) -> list[UserListItem]:
    return await list_users(db, skip, limit)  # type: ignore[return-value]


@router.get("/users/{user_id}", response_model=UserListItem)
async def admin_get_user(
    user_id: str,
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserListItem:
    user = await get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    return user  # type: ignore[return-value]


@router.put("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: str,
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not await set_user_active(db, user_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    return {"message": "User activated."}


@router.put("/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "SELF_ACTION", "message": "Cannot deactivate your own account."}},
        )
    if not await set_user_active(db, user_id, False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    return {"message": "User deactivated."}


@router.put("/users/{user_id}/role")
async def admin_update_role(
    user_id: str,
    payload: RoleUpdate,
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    user = await update_user_role(db, user_id, payload.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)
    return {"message": f"Role updated to {payload.role}."}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "SELF_DELETE", "message": "Cannot delete your own account."}},
        )
    if not await delete_user(db, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_404)


# ── Analyses ───────────────────────────────────────────────────────────────────

@router.get("/analyses", response_model=list[AnalysisSummary])
async def admin_list_analyses(
    _: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> list[AnalysisSummary]:
    return await list_all_analyses(db, skip, limit)  # type: ignore[return-value]


# ── Brains sidecar pool (Task A3.4) ──────────────────────────────────────────

_INVALID_PIN = {
    "error": {
        "code": "INVALID_PIN_URL",
        "message": "url must be one of the configured BRAINS_SERVICE_URLS pool entries, or null to unpin.",
    }
}


@router.get("/brains", response_model=list[BrainsPoolEntry])
async def admin_brains_pool(
    _: Annotated[User, Depends(get_current_admin)],
) -> list[BrainsPoolEntry]:
    return await brains_registry.pool_status()  # type: ignore[return-value]


@router.post("/brains/pin")
async def admin_brains_pin(
    payload: BrainsPinRequest,
    _: Annotated[User, Depends(get_current_admin)],
) -> dict:
    # Never accept an arbitrary URL here -- that would be an SSRF hole behind
    # an admin-authenticated endpoint. null always unpins; any non-null value
    # must already be in the configured pool.
    if payload.url is not None and payload.url not in brains_registry.configured_urls():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_INVALID_PIN)
    brains_registry.set_pin(payload.url)
    return {"pinned": brains_registry.get_pin()}
