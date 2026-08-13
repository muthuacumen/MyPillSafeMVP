"""Outbound SMTP for the public contact form.

Inert by default and transport-agnostic on purpose. The repo has never had a
mail path, and the host (IONOS, per mypillsafe.ca's MX/SPF records) is not
decided at the code level — so this ships with NO credentials anywhere and
does nothing at all until SMTP_HOST/SMTP_USER/SMTP_PASSWORD are filled in on
the droplet. Any RFC-compliant relay works: IONOS, a Gmail app password,
anything else.

The mailbox is a NOTIFICATION channel, not the system of record. The route
writes the JSONL log first and treats every outcome here as advisory — see
app/api/v1/routes/contact.py.
"""
import logging
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

# A wedged relay must not become a wedged request. The contact form is a
# synchronous POST a human is waiting on, so the whole SMTP conversation gets
# a hard ceiling rather than inheriting a library default measured in minutes.
_SMTP_TIMEOUT_SECONDS = 10


def is_configured() -> bool:
    """True only when there is a full credential set to attempt a send with."""
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _build_message(full_name: str, email: str, message: str) -> EmailMessage:
    msg = EmailMessage()
    # From must be an address the relay will accept as its own sender —
    # falling back to SMTP_USER is right for every provider that authenticates
    # by mailbox (IONOS and Gmail both do), and stops a blank From being sent.
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = settings.CONTACT_TO
    msg["Subject"] = f"MyPillSafe contact form — {full_name}"
    # The whole point of the mailbox: hitting Reply in it answers the person
    # who wrote in, not the app's own sending address.
    msg["Reply-To"] = email
    msg.set_content(
        f"New contact form submission from mypillsafe.ca\n\n"
        f"Name:  {full_name}\n"
        f"Email: {email}\n\n"
        f"Message:\n{message}\n"
    )
    return msg


async def send_contact_email(full_name: str, email: str, message: str) -> bool:
    """Send one contact notification. False = not sent, never an exception.

    Returns False (without opening a socket) when SMTP is unconfigured, which
    is the default state of this repo and of any deploy that hasn't filled in
    the vars yet.
    """
    if not is_configured():
        logger.debug("SMTP not configured — contact email skipped")
        return False

    try:
        import aiosmtplib
    except ImportError:
        # requirements.txt pins aiosmtplib, but a stale venv shouldn't 500 a
        # public form — degrade to log-only, exactly like "not configured".
        logger.error("aiosmtplib is not installed — contact email skipped")
        return False

    try:
        await aiosmtplib.send(
            _build_message(full_name, email, message),
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_STARTTLS,
            timeout=_SMTP_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 — every relay failure is advisory
        # str(exc) only: aiosmtplib exceptions carry the server's reply, never
        # the credentials. Nothing here may ever render settings.SMTP_PASSWORD.
        logger.error("Contact email send failed via %s: %s", settings.SMTP_HOST, exc)
        return False

    logger.info("Contact email delivered to %s", settings.CONTACT_TO)
    return True
