"""Boot-time admin promotion from the ADMIN_EMAILS env var.

WHY THIS EXISTS: `/dev/seed-admin` 404s unless `APP_ENV == "development"`
(app/api/v1/routes/dev.py), so before this there was NO way to mint an admin
on the production droplet — and with registration now admin-gated, an
approval queue with nobody able to approve is a locked door with the key
inside. This is the key: put an address in ADMIN_EMAILS, restart, and that
account is an admin.

It PROMOTES, it never CREATES. Creating an account would mean inventing a
password (or leaving a blank-credential admin sitting in production), so the
flow is deliberately two-step: Muthu registers through the normal form like
anyone else, then a restart promotes him. An email with no matching user is a
logged no-op, which is the expected state between deploy and first signup.
"""
import logging

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


def configured_admin_emails() -> list[str]:
    """ADMIN_EMAILS parsed to a lowercased, de-duplicated, order-stable list."""
    seen: dict[str, None] = {}
    for raw in settings.ADMIN_EMAILS.split(","):
        email = raw.strip().lower()
        if email:
            seen.setdefault(email, None)
    return list(seen)


async def promote_configured_admins() -> int:
    """Make every ADMIN_EMAILS match an active ADMIN. Returns rows changed.

    Idempotent by construction: a second run finds every target already
    `ADMIN`/active and writes nothing, so the returned count is 0 — which is
    what the test asserts rather than just "it didn't crash".
    """
    emails = configured_admin_emails()
    if not emails:
        return 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(func.lower(User.email).in_(emails))
        )
        users = result.scalars().all()

        found = {user.email.lower() for user in users}
        for missing in (e for e in emails if e not in found):
            # Not an error — this is simply "hasn't registered yet". The next
            # restart after they sign up will pick them up.
            logger.info(
                "ADMIN_EMAILS: no account yet for %s — will promote on a later restart",
                missing,
            )

        changed = 0
        for user in users:
            already = user.role == UserRole.ADMIN.value and user.is_active
            if already:
                logger.info("ADMIN_EMAILS: %s is already an active admin", user.email)
                continue
            user.role = UserRole.ADMIN.value
            user.is_active = True
            changed += 1
            logger.info("ADMIN_EMAILS: promoted %s to active ADMIN", user.email)

        if changed:
            await session.commit()

    logger.info(
        "ADMIN_EMAILS: %d configured, %d matched, %d promoted",
        len(emails), len(users), changed,
    )
    return changed


async def promote_configured_admins_safely() -> None:
    """Startup wrapper — a DB hiccup here must never stop the app booting.

    Boot-time work that can raise is how a deploy turns into an outage. The
    promotion is a convenience; the app is perfectly serviceable without it,
    and the next restart retries. So: log loudly, keep going.
    """
    try:
        await promote_configured_admins()
    except Exception:  # noqa: BLE001 — deliberately broad, see docstring
        logger.exception("ADMIN_EMAILS promotion failed — continuing startup")
