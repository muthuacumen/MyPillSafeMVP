"""Public contact form (Priority 3 /contact) — logs submissions, no auth required."""
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.services.mail_service import send_contact_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact", tags=["contact"])


class ContactRequest(BaseModel):
    full_name: str
    email: EmailStr
    message: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_contact_message(payload: ContactRequest) -> dict:
    logger.info("Contact form submission from %s <%s>", payload.full_name, payload.email)

    log_path = os.path.join(settings.UPLOAD_DIR, "contact_messages.jsonl")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    entry = {
        "full_name": payload.full_name,
        "email": payload.email,
        "message": payload.message,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    # Mail is attempted only AFTER the submission is durably on disk, and its
    # result never reaches the caller. The JSONL file is the system of record;
    # the mailbox is a convenience. A message must never be lost because a
    # relay was down, misconfigured, or (the default) not configured at all.
    if not await send_contact_email(payload.full_name, payload.email, payload.message):
        logger.info("Contact submission logged only (no email sent): %s", payload.email)

    return {"message": "Thank you — we received your message and will respond soon."}
