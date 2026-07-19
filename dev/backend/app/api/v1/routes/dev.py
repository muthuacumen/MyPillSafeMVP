from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/dev", tags=["dev"])

_DEV_ONLY = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _guard():
    if settings.APP_ENV != "development":
        raise _DEV_ONLY


class SeedAdminRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = "Admin"
    last_name: str = "User"


@router.post(
    "/seed-admin",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Bootstrap first admin (dev only)",
    description=(
        "**Development only** — returns 404 in production.\n\n"
        "- If the email **already exists**, that account is promoted to `ADMIN` and reactivated.\n"
        "- If the email is **new**, a fresh `ADMIN` account is created.\n\n"
        "Copy the returned `access_token`, click **Authorize** above, and paste it to unlock all admin endpoints."
    ),
)
async def seed_admin(
    payload: SeedAdminRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _guard()

    result = await db.execute(
        select(User).options(selectinload(User.patient)).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if user:
        user.role = UserRole.ADMIN.value
        user.is_active = True
    else:
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=UserRole.ADMIN.value,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        patient = Patient(
            user_id=user.id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=date(1990, 1, 1),
        )
        db.add(patient)

    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
