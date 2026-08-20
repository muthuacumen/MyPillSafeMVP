"""Real session termination via `users.token_version` (Task T2).

Every access/refresh token mints a `tv` claim equal to the user's
`token_version` at issuance (app/core/security.py). Validation --
`get_current_user` (app/api/deps.py) and the refresh flow
(auth_service.refresh_tokens) -- 401s any token whose `tv` no longer matches
the live column. Bumping `token_version` (POST
/admin/users/{id}/terminate-sessions, or as a side effect of deactivate) is
what actually invalidates tokens a user is already holding -- unlike
`is_active`, which only ever blocked NEW logins/refreshes.
"""
import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import _make_token, create_access_token, create_refresh_token
from app.models.user import User


def _signup(email: str) -> dict:
    return {
        "email": email,
        "password": "Test1234",
        "first_name": "Term",
        "last_name": "Test",
        "date_of_birth": "1990-01-01",
    }


def _fresh_email(prefix: str = "term") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@pillsafe.dev"


# --- back-compat: a token with no `tv` claim behaves like tv=0 -------------


@pytest.mark.asyncio
async def test_token_missing_tv_claim_is_treated_as_zero(
    client: AsyncClient, db_session: AsyncSession, approve_user
):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)

    # Simulates a token minted before this feature existed -- no `tv` key at
    # all, not `tv=0` explicitly.
    legacy_token = _make_token(
        {"sub": user.id, "role": user.role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert response.status_code == 200


# --- terminate-sessions bumps token_version and kills the old token --------


@pytest.mark.asyncio
async def test_terminate_sessions_invalidates_existing_access_token(
    client: AsyncClient, db_session: AsyncSession, approve_user, admin_headers: dict
):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)
    old_token = create_access_token(user.id, user.role, user.token_version)

    still_good = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert still_good.status_code == 200

    term_resp = await client.post(
        f"/api/v1/admin/users/{user.id}/terminate-sessions", headers=admin_headers
    )
    assert term_resp.status_code == 200
    assert term_resp.json()["token_version"] == 1

    now_rejected = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert now_rejected.status_code == 401

    # A FRESH token, minted after termination, must work.
    result = await db_session.execute(select(User).where(User.id == user.id))
    refreshed_user = result.scalar_one()
    assert refreshed_user.token_version == 1
    new_token = create_access_token(
        refreshed_user.id, refreshed_user.role, refreshed_user.token_version
    )
    works_again = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}
    )
    assert works_again.status_code == 200


@pytest.mark.asyncio
async def test_terminate_sessions_unknown_user_404s(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/admin/users/does-not-exist/terminate-sessions", headers=admin_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_terminate_sessions_requires_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/users/whatever/terminate-sessions", headers=auth_headers
    )
    assert resp.status_code == 403


# --- refresh flow honours the same tv check ---------------------------------


@pytest.mark.asyncio
async def test_refresh_with_terminated_session_is_401(
    client: AsyncClient, db_session: AsyncSession, approve_user, admin_headers: dict
):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)
    old_refresh = create_refresh_token(user.id, user.token_version)

    await client.post(f"/api/v1/admin/users/{user.id}/terminate-sessions", headers=admin_headers)

    resp = await client.post(
        "/api/v1/auth/refresh", cookies={"refresh_token": old_refresh}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "TOKEN_REVOKED"


# --- deactivate now also bumps token_version (closes the known gap) --------


@pytest.mark.asyncio
async def test_deactivate_bumps_token_version_and_kills_live_session(
    client: AsyncClient, db_session: AsyncSession, approve_user, admin_headers: dict
):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)
    old_token = create_access_token(user.id, user.role, user.token_version)

    deactivate_resp = await client.put(
        f"/api/v1/admin/users/{user.id}/deactivate", headers=admin_headers
    )
    assert deactivate_resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one().token_version == 1

    # The already-issued token is dead immediately -- this was the known gap
    # (deactivate used to only block a FUTURE login/refresh).
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_increment_token_version_uses_atomic_update_expression(
    client: AsyncClient, db_session: AsyncSession, approve_user
):
    """Regression for the lost-update bug: `increment_token_version` used to
    do `user.token_version += 1` -- a Python read-modify-write -- so two
    concurrent admin actions on the same user could both read N and both
    write N + 1, silently losing a bump. The fix is an atomic
    `UPDATE ... SET token_version = token_version + 1` SQL expression, which
    has no such window because the database computes new = old + 1 as part
    of one statement.

    SQLite (used in these tests) can't easily prove the race itself -- both
    a buggy and a fixed implementation pass a simple "call it twice
    sequentially" check, since nothing here is actually concurrent. So this
    test asserts on the *construct* directly: `admin_service.increment_token_version`
    must build its UPDATE via a SQL column expression (`token_version =
    token_version + 1`), not by mutating a loaded ORM instance's attribute --
    which is exactly what closes the race in production under real
    concurrent writers.
    """
    import inspect

    from app.services import admin_service

    source = inspect.getsource(admin_service.increment_token_version)
    assert "token_version + 1" in source, (
        "increment_token_version must compute the new value with a SQL "
        "expression (token_version = token_version + 1), not a Python "
        "read-modify-write, to stay atomic under concurrent callers"
    )
    assert "+=" not in source, (
        "increment_token_version must not use a Python '+=' read-modify-write "
        "on a loaded ORM attribute -- that reintroduces the lost-update race"
    )

    # Belt-and-braces behavioural check: two sequential calls still land
    # +1 each, and each call's returned value matches the persisted row.
    email = _fresh_email("atomic")
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)
    starting_version = user.token_version

    first = await admin_service.increment_token_version(db_session, user.id)
    second = await admin_service.increment_token_version(db_session, user.id)
    assert (first, second) == (starting_version + 1, starting_version + 2)

    result = await db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one().token_version == second


@pytest.mark.asyncio
async def test_old_token_stays_dead_after_deactivate_then_reactivate(
    client: AsyncClient, db_session: AsyncSession, approve_user, admin_headers: dict
):
    """THE ACTUAL GAP: `is_active` alone is a toggle, not a kill -- flip it
    back on and a pre-deactivation token that was merely BLOCKED (not
    invalidated) would start working again. `token_version` only ever
    increments, so a token minted before a deactivate/reactivate cycle must
    stay dead forever, even once the account is active again.
    """
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    user = await approve_user(email)
    old_token = create_access_token(user.id, user.role, user.token_version)

    await client.put(f"/api/v1/admin/users/{user.id}/deactivate", headers=admin_headers)
    await client.put(f"/api/v1/admin/users/{user.id}/activate", headers=admin_headers)

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert resp.status_code == 401
