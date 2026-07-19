"""Multilingual medication reminder messages — hardcoded templates, zero external API calls."""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_patient
from app.models.user import User

router = APIRouter(prefix="/reminders", tags=["reminders"])

_TEMPLATES: dict[str, str] = {
    "en": (
        "Hi {name}, according to your prescription, it's time to take {medication}. "
        "Please take it as directed by your doctor."
    ),
    "fr": (
        "Bonjour {name}, selon votre ordonnance, il est temps de prendre {medication}. "
        "Veuillez le prendre comme indiqué par votre médecin."
    ),
    "ar": (
        "مرحباً {name}، وفقاً لوصفتك الطبية، حان وقت تناول {medication}. "
        "يرجى تناوله كما وصفه طبيبك."
    ),
    "es": (
        "Hola {name}, según su receta médica, es hora de tomar {medication}. "
        "Por favor tómelo según las indicaciones de su médico."
    ),
}
_FALLBACK = "en"


class ReminderRequest(BaseModel):
    medication_name: str
    patient_first_name: str
    language: str = "en"


class ReminderResponse(BaseModel):
    message: str
    language: str


@router.post("/message", response_model=ReminderResponse)
async def get_reminder_message(
    payload: ReminderRequest,
    _current_user: Annotated[User, Depends(get_current_patient)],
) -> ReminderResponse:
    # Normalise "en-CA" -> "en"
    lang = payload.language.lower().strip().split("-")[0]
    template = _TEMPLATES.get(lang, _TEMPLATES[_FALLBACK])
    message = template.format(
        name=payload.patient_first_name,
        medication=payload.medication_name,
    )
    return ReminderResponse(message=message, language=lang)
