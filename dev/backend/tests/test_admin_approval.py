"""Admin-approval registration gate + the ADMIN_EMAILS boot-time promotion.

The load-bearing test in here is test_login_wrong_password_on_pending_account_is_401.
Introducing a distinct ACCOUNT_PENDING_APPROVAL answer is exactly how a login
endpoint turns into an account-enumeration oracle: if the new code leaks
before the password is checked, anyone can ask "is this email registered?"
and read the answer off the status code. Password first, state second — and
that ordering is asserted, not just written.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, UserRole
from app.services.admin_bootstrap import promote_configured_admins


def _signup(email: str) -> dict:
    return {
        "email": email,
        "password": "Test1234",
        "first_name": "Pending",
        "last_name": "User",
        "date_of_birth": "1990-01-01",
    }


def _fresh_email(prefix: str = "pending") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@pillsafe.dev"


# ── The gate ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_returns_202_and_creates_inactive_user(
    client: AsyncClient, db_session: AsyncSession
):
    email = _fresh_email()
    response = await client.post("/api/v1/auth/register", json=_signup(email))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending_approval"
    assert "access_token" not in body
    # No refresh cookie either — the browser must leave holding nothing usable.
    assert "refresh_token" not in response.cookies

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    assert user.is_active is False
    assert user.role == UserRole.PATIENT.value


@pytest.mark.asyncio
async def test_register_still_creates_the_patient_row(
    client: AsyncClient, db_session: AsyncSession
):
    """The profile must exist before approval, or approving yields a broken
    account with no name, DOB or language."""
    email = _fresh_email("profile")
    await client.post("/api/v1/auth/register", json=_signup(email))

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    await db_session.refresh(user, ["patient"])
    assert user.patient is not None
    assert user.patient.first_name == "Pending"


@pytest.mark.asyncio
async def test_login_pending_account_right_password_is_403(client: AsyncClient):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Test1234"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "ACCOUNT_PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_login_wrong_password_on_pending_account_is_401(client: AsyncClient):
    """THE ENUMERATION GUARD. A wrong password must be indistinguishable from
    an unknown email — same status, same code — no matter what state the
    account is in."""
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))

    pending = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "WrongPass9"}
    )
    unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": _fresh_email("nosuch"), "password": "WrongPass9"},
    )

    assert pending.status_code == 401
    assert pending.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"
    # Byte-identical answers, not merely both-in-the-4xx-range.
    assert pending.status_code == unknown.status_code
    assert pending.json() == unknown.json()


@pytest.mark.asyncio
async def test_approved_account_can_log_in(client: AsyncClient, approve_user):
    email = _fresh_email()
    await client.post("/api/v1/auth/register", json=_signup(email))
    await approve_user(email)

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Test1234"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_kill_switch_restores_immediate_login(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """REQUIRE_ADMIN_APPROVAL=false must be byte-for-byte the old behaviour:
    201, a token, a refresh cookie, and an active account."""
    monkeypatch.setattr(settings, "REQUIRE_ADMIN_APPROVAL", False)
    email = _fresh_email("killswitch")

    response = await client.post("/api/v1/auth/register", json=_signup(email))

    assert response.status_code == 201
    assert response.json()["access_token"]
    assert "refresh_token" in response.cookies

    result = await db_session.execute(select(User).where(User.email == email))
    assert result.scalar_one().is_active is True


# ── ADMIN_EMAILS boot-time promotion ─────────────────────────────────────────
#
# These drive promote_configured_admins() against the app's real session
# factory, so they need the app engine's tables to exist rather than the test
# engine's. `_bootstrap_db` points AsyncSessionLocal at the test database for
# the duration of the test, which is the same seam the client fixture uses.

@pytest.fixture
def admin_emails(monkeypatch: pytest.MonkeyPatch):
    def _set(value: str) -> None:
        monkeypatch.setattr(settings, "ADMIN_EMAILS", value)

    return _set


@pytest.fixture
def bootstrap_session(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession):
    """Make admin_bootstrap's `async with AsyncSessionLocal()` yield the test
    session, so its writes land in the same transaction the assertions read."""
    class _SingleSessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_exc):
            return False

    import app.services.admin_bootstrap as bootstrap

    monkeypatch.setattr(bootstrap, "AsyncSessionLocal", _SingleSessionFactory())
    # The real commit would end the test transaction and defeat rollback.
    monkeypatch.setattr(db_session, "commit", db_session.flush)


@pytest.mark.asyncio
async def test_bootstrap_promotes_matching_user_and_is_idempotent(
    client: AsyncClient, db_session: AsyncSession, admin_emails, bootstrap_session
):
    email = _fresh_email("boss")
    await client.post("/api/v1/auth/register", json=_signup(email))
    admin_emails(f"  {email.upper()} ")  # whitespace + case must not matter

    assert await promote_configured_admins() == 1

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    assert user.role == UserRole.ADMIN.value
    assert user.is_active is True

    # Second run changes nothing — that is what "idempotent" has to mean here,
    # not merely "doesn't raise".
    assert await promote_configured_admins() == 0
    assert user.role == UserRole.ADMIN.value
    assert user.is_active is True


@pytest.mark.asyncio
async def test_bootstrap_with_unknown_email_is_a_noop(
    admin_emails, bootstrap_session
):
    admin_emails(_fresh_email("never-registered"))
    assert await promote_configured_admins() == 0


@pytest.mark.asyncio
async def test_bootstrap_with_empty_setting_is_a_noop(admin_emails, bootstrap_session):
    admin_emails("")
    assert await promote_configured_admins() == 0


@pytest.mark.asyncio
async def test_bootstrap_promotes_several_and_skips_unknown(
    client: AsyncClient, db_session: AsyncSession, admin_emails, bootstrap_session
):
    first, second = _fresh_email("a1"), _fresh_email("a2")
    for email in (first, second):
        await client.post("/api/v1/auth/register", json=_signup(email))
    admin_emails(f"{first},{_fresh_email('ghost')},{second}")

    assert await promote_configured_admins() == 2

    result = await db_session.execute(
        select(User).where(User.email.in_([first, second]))
    )
    for user in result.scalars().all():
        assert user.role == UserRole.ADMIN.value
        assert user.is_active is True


@pytest.mark.asyncio
async def test_bootstrap_failure_never_stops_startup(monkeypatch: pytest.MonkeyPatch):
    """A DB hiccup at boot must be logged and swallowed. Booting into a broken
    promotion is recoverable; not booting at all is an outage."""
    import app.services.admin_bootstrap as bootstrap

    async def _explode():
        raise RuntimeError("database is not accepting connections")

    monkeypatch.setattr(bootstrap, "promote_configured_admins", _explode)
    await bootstrap.promote_configured_admins_safely()  # must not raise
