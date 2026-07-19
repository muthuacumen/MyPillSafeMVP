"""Multilingual, plain-language prescription instructions.

Extends the reminders.py templated-translation pattern (dict templates,
zero external API calls) to a fuller sentence covering dosage, computed
dose times, food timing, purpose, and PRN max-dose guidance. Built
entirely from structured fields already extracted by
prescription_parser.py — never a literal translation of raw OCR text —
because no LLM/translation API is configured for this deployment.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_patient
from app.models.user import User

router = APIRouter(prefix="/instructions", tags=["instructions"])

_FALLBACK = "en"
_CONJ = {"en": "and", "fr": "et", "es": "y", "ar": "و"}

_SCHEDULED: dict[str, str] = {
    "en": "Take {drug}{dosage} at {times}{food}{purpose}.",
    "fr": "Prenez {drug}{dosage} à {times}{food}{purpose}.",
    "es": "Tome {drug}{dosage} a las {times}{food}{purpose}.",
    "ar": "تناول {drug}{dosage} في {times}{food}{purpose}.",
}
_PRN: dict[str, str] = {
    "en": "Take {drug}{dosage} as needed{purpose}{max}.",
    "fr": "Prenez {drug}{dosage} en cas de besoin{purpose}{max}.",
    "es": "Tome {drug}{dosage} cuando sea necesario{purpose}{max}.",
    "ar": "تناول {drug}{dosage} عند الحاجة{purpose}{max}.",
}
_FOOD: dict[str, str] = {
    "en": ", with food",
    "fr": ", avec de la nourriture",
    "es": ", con alimentos",
    "ar": "، مع الطعام",
}
_PURPOSE: dict[str, str] = {
    "en": " for {p}",
    "fr": " pour {p}",
    "es": " para {p}",
    "ar": " من أجل {p}",
}
_MAX: dict[str, str] = {
    "en": ". Do not take more than {n} in 24 hours",
    "fr": ". Ne dépassez pas {n} en 24 heures",
    "es": ". No tome más de {n} en 24 horas",
    "ar": "، ولا تتناول أكثر من {n} في 24 ساعة",
}


def _fmt_clock(hhmm: str) -> str:
    hour, minute = map(int, hhmm.split(":"))
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12}:{minute:02d} {suffix}"


def _fmt_times(times: list[str], lang: str) -> str:
    labels = [_fmt_clock(t) for t in times]
    if len(labels) <= 1:
        return labels[0] if labels else ""
    return ", ".join(labels[:-1]) + f" {_CONJ.get(lang, 'and')} {labels[-1]}"


class InstructionRequest(BaseModel):
    drug_name: str
    dosage: str | None = None
    frequency_type: str = "UNKNOWN"
    specific_times: list[str] = []
    with_food: bool = False
    purpose: str | None = None
    max_daily_dose: int | None = None
    language: str = "en"


class InstructionResponse(BaseModel):
    message: str
    language: str


@router.post("/message", response_model=InstructionResponse)
async def get_instruction_message(
    payload: InstructionRequest,
    _current_user: Annotated[User, Depends(get_current_patient)],
) -> InstructionResponse:
    lang = payload.language.lower().strip().split("-")[0]
    if lang not in _SCHEDULED:
        lang = _FALLBACK

    dosage = f" {payload.dosage}" if payload.dosage else ""
    food = _FOOD[lang] if payload.with_food else ""
    purpose = _PURPOSE[lang].format(p=payload.purpose) if payload.purpose else ""

    if payload.frequency_type == "PRN":
        max_clause = _MAX[lang].format(n=payload.max_daily_dose) if payload.max_daily_dose else ""
        message = _PRN[lang].format(drug=payload.drug_name, dosage=dosage, purpose=purpose, max=max_clause)
    else:
        times = _fmt_times(payload.specific_times, lang) or "your scheduled times"
        message = _SCHEDULED[lang].format(
            drug=payload.drug_name, dosage=dosage, times=times, food=food, purpose=purpose
        )

    return InstructionResponse(message=message, language=lang)
