import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.auth_service import get_user_by_id

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"error": {"code": "UNAUTHORIZED", "message": "Invalid or expired token."}},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise _UNAUTH

    if payload.get("type") != "access":
        raise _UNAUTH

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise _UNAUTH

    user = await get_user_by_id(db, user_id)
    if not user:
        raise _UNAUTH
    return user


_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"error": {"code": "FORBIDDEN", "message": "Admin access required."}},
)


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise _FORBIDDEN
    return current_user


_ADMIN_BLOCKED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"error": {"code": "FORBIDDEN", "message": "Admins cannot access patient health data."}},
)


async def get_current_patient(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Patient-data-only endpoints (prescriptions, scans): admins get 403, never patient PHI."""
    if current_user.role == UserRole.ADMIN.value:
        raise _ADMIN_BLOCKED
    return current_user
