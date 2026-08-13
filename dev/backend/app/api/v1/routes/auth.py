from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    PendingApprovalResponse,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import (
    AuthError,
    login_user,
    refresh_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_REFRESH_COOKIE = "refresh_token"
_REFRESH_PATH = "/api/v1/auth/refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=_REFRESH_PATH,
    )


@router.post(
    "/register",
    # Two status codes with two different bodies, so the response model is
    # declared per-code below instead of once for the route. `response_model=
    # None` is load-bearing: without it FastAPI infers a model from the return
    # annotation and would try to validate the 202 body as a TokenResponse.
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "model": TokenResponse,
            "description": "Account created and signed in (approval disabled).",
        },
        202: {
            "model": PendingApprovalResponse,
            "description": "Account created, awaiting admin approval. No tokens issued.",
        },
    },
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse | PendingApprovalResponse:
    try:
        _user, access_token, refresh_token = await register_user(db, payload)
    except AuthError as exc:
        http_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "EMAIL_TAKEN"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=http_code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc

    if access_token is None or refresh_token is None:
        # Pending approval: no tokens, and critically no refresh cookie —
        # the browser must leave this exchange holding nothing it can use.
        response.status_code = status.HTTP_202_ACCEPTED
        return PendingApprovalResponse(
            message=(
                "Your account has been created and is awaiting administrator "
                "approval. You'll be able to sign in once it's approved."
            ),
        )

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        _user, access_token, refresh_token = await login_user(db, payload)
    except AuthError as exc:
        # 403, not 401: the credentials were correct, the account just isn't
        # allowed in yet. 401 would tell the client to re-prompt for a
        # password that is already right.
        http_code = (
            status.HTTP_403_FORBIDDEN
            if exc.code == "ACCOUNT_PENDING_APPROVAL"
            else status.HTTP_401_UNAUTHORIZED
        )
        raise HTTPException(
            status_code=http_code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(_REFRESH_COOKIE, path=_REFRESH_PATH)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_REFRESH_TOKEN",
                    "message": "No refresh token provided.",
                }
            },
        )
    try:
        new_access, new_refresh = await refresh_tokens(db, token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=new_access,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=MeResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    patient = current_user.patient
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        first_name=patient.first_name if patient else None,
        last_name=patient.last_name if patient else None,
        medications_analyzed=patient.medications_analyzed if patient else 0,
    )
