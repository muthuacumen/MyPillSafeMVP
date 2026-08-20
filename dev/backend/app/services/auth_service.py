import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import JWTError

from app.models.user import User, UserRole
from app.models.patient import Patient
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


async def register_user(
    db: AsyncSession, payload: RegisterRequest
) -> tuple[User, str | None, str | None]:
    """Create the account. Tokens are None when the signup needs approval.

    The optional-token return is deliberate. Returning empty strings would
    typecheck identically and let a caller set a refresh cookie containing ""
    without anything complaining -- None makes the route's two paths
    structurally different and impossible to conflate.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise AuthError("An account with this email already exists.", code="EMAIL_TAKEN")

    needs_approval = settings.REQUIRE_ADMIN_APPROVAL
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.PATIENT.value,
        is_active=not needs_approval,
    )
    db.add(user)
    await db.flush()

    patient = Patient(
        user_id=user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        preferred_language=payload.preferred_language,
    )
    db.add(patient)
    await db.flush()

    if needs_approval:
        logger.info("User registered, awaiting admin approval: %s", user.email)
        return user, None, None

    logger.info("User registered: %s", user.email)
    return (
        user,
        create_access_token(user.id, user.role, user.token_version),
        create_refresh_token(user.id, user.token_version),
    )


async def login_user(db: AsyncSession, payload: LoginRequest) -> tuple[User, str, str]:
    """Authenticate, then gate on approval -- in that order, deliberately.

    This used to filter `is_active` in the SQL, which was fine when the flag
    only ever meant "an admin switched this account off". Now that every new
    signup starts inactive, the check has to move out of the WHERE clause:
    with it there, a pending account and a non-existent account are the same
    row-not-found, so once ACCOUNT_PENDING_APPROVAL exists as a distinct
    answer, an unauthenticated caller could enumerate which emails have
    registered just by watching 403 vs 401.

    So: fetch by email only, verify the password FIRST, and reveal the
    account's state ONLY to someone who already proved they own it. A wrong
    password is the generic INVALID_CREDENTIALS whatever the account's state
    -- including for an email that does not exist at all.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.patient))
        .where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise AuthError("Invalid email or password.", code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise AuthError(
            "Your account is awaiting administrator approval.",
            code="ACCOUNT_PENDING_APPROVAL",
        )

    access_token = create_access_token(user.id, user.role, user.token_version)
    refresh_token = create_refresh_token(user.id, user.token_version)
    logger.info("User logged in: %s", user.email)
    return user, access_token, refresh_token


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise AuthError("Invalid or expired refresh token.", code="INVALID_REFRESH_TOKEN") from exc

    if payload.get("type") != "refresh":
        raise AuthError("Token type mismatch.", code="TOKEN_TYPE_MISMATCH")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User)
        .options(selectinload(User.patient))
        .where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AuthError("User not found or inactive.", code="USER_NOT_FOUND")

    # Same session-termination check as get_current_user (Task T2). A missing
    # `tv` is tv=0 for back-compat with refresh tokens minted before this
    # claim existed; anything else that doesn't match the live column is a
    # terminated session trying to mint itself a fresh access token, which is
    # exactly the hole this check exists to close.
    if payload.get("tv", 0) != user.token_version:
        raise AuthError("Session has been terminated.", code="TOKEN_REVOKED")

    return (
        create_access_token(user.id, user.role, user.token_version),
        create_refresh_token(user.id, user.token_version),
    )


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.patient))
        .where(User.id == user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()
