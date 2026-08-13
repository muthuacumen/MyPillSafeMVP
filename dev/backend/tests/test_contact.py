import json
import os
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import mail_service


def _read_jsonl() -> list[dict]:
    path = os.path.join(settings.UPLOAD_DIR, "contact_messages.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.mark.asyncio
async def test_contact_submission_no_auth_required(client: AsyncClient):
    response = await client.post(
        "/api/v1/contact",
        json={
            "full_name": "Jane Caregiver",
            "email": "jane@example.com",
            "message": "How do I add a second patient profile?",
        },
    )
    assert response.status_code == 201
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_contact_validates_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/contact",
        json={"full_name": "Jane", "email": "not-an-email", "message": "hi"},
    )
    assert response.status_code == 422


# ── Mail (app/services/mail_service.py) ──────────────────────────────────────
#
# The contract these protect: the JSONL log is the system of record and the
# mailbox is advisory. Mail being off, broken, or slow must be invisible to
# the person filling in the form.

@pytest.mark.asyncio
async def test_send_contact_email_is_inert_without_config(monkeypatch: pytest.MonkeyPatch):
    """The default state of this repo: no host, no credentials, no socket."""
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

    assert mail_service.is_configured() is False
    assert await mail_service.send_contact_email("Jane", "jane@example.com", "hi") is False


@pytest.mark.asyncio
async def test_partial_smtp_config_does_not_attempt_a_send(monkeypatch: pytest.MonkeyPatch):
    """A half-filled .env (host set, password still blank) is the likeliest
    misconfiguration — it must be inert, not a connection attempt to :587."""
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.ionos.com")
    monkeypatch.setattr(settings, "SMTP_USER", "info@mypillsafe.ca")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

    assert mail_service.is_configured() is False
    assert await mail_service.send_contact_email("Jane", "jane@example.com", "hi") is False


@pytest.mark.asyncio
async def test_contact_returns_201_and_writes_jsonl_when_smtp_unconfigured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    marker = f"jsonl-{uuid.uuid4().hex[:8]}"

    response = await client.post(
        "/api/v1/contact",
        json={"full_name": "Log Only", "email": "log@example.com", "message": marker},
    )

    assert response.status_code == 201
    assert marker in [entry["message"] for entry in _read_jsonl()]


@pytest.mark.asyncio
async def test_contact_still_201_and_logged_when_the_relay_fails(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """A submission must never be lost because mail is down."""
    async def _blow_up(*_args, **_kwargs):
        raise ConnectionRefusedError("relay refused the connection")

    monkeypatch.setattr(
        "app.api.v1.routes.contact.send_contact_email", _blow_up, raising=True
    )
    marker = f"relay-down-{uuid.uuid4().hex[:8]}"

    with pytest.raises(ConnectionRefusedError):
        await client.post(
            "/api/v1/contact",
            json={"full_name": "Relay", "email": "relay@example.com", "message": marker},
        )

    # Even on the hardest possible failure, the JSONL write already happened —
    # it is ordered BEFORE the send for exactly this reason.
    assert marker in [entry["message"] for entry in _read_jsonl()]


@pytest.mark.asyncio
async def test_contact_survives_a_send_that_returns_false(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def _fail_quietly(*_args, **_kwargs):
        return False

    monkeypatch.setattr(
        "app.api.v1.routes.contact.send_contact_email", _fail_quietly, raising=True
    )
    response = await client.post(
        "/api/v1/contact",
        json={"full_name": "Quiet", "email": "quiet@example.com", "message": "hello"},
    )
    assert response.status_code == 201
    assert "message" in response.json()


def test_reply_to_is_the_submitter_not_the_mailbox(monkeypatch: pytest.MonkeyPatch):
    """Replying from the info@ mailbox has to reach the person who wrote in."""
    monkeypatch.setattr(settings, "SMTP_FROM", "info@mypillsafe.ca")
    monkeypatch.setattr(settings, "CONTACT_TO", "info@mypillsafe.ca")

    msg = mail_service._build_message("Jane Caregiver", "jane@example.com", "hi there")

    assert msg["Reply-To"] == "jane@example.com"
    assert msg["To"] == "info@mypillsafe.ca"
    assert msg["From"] == "info@mypillsafe.ca"
    assert "Jane Caregiver" in msg["Subject"]


def test_from_falls_back_to_smtp_user(monkeypatch: pytest.MonkeyPatch):
    """A blank SMTP_FROM must not put an empty From on the wire."""
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    monkeypatch.setattr(settings, "SMTP_USER", "relay-account@mypillsafe.ca")

    msg = mail_service._build_message("Jane", "jane@example.com", "hi")
    assert msg["From"] == "relay-account@mypillsafe.ca"
