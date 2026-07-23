"""MyPillSafe Assistant -- public (no-auth) project-explainer chatbot (Phase 5).

Distinct from `/api/v1/qa/chat` (BB3 + CB4, authenticated, DIN-scoped
medication Q&A): this widget only explains the MyPillSafe PROJECT -- how it
works, its safety design, the research behind it, and the team -- from the
curated `app/data/assistant_kb.json`. It never answers medication-specific
questions; a keyword gate (`assistant_kb.is_medication_intent`) redirects
those to `/dashboard/qa` before any KB lookup or LLM call happens.

`POST /chat` -- confidence-zone routing over `assistant_kb.retrieve()`:
    medication-intent gate hit -> redirect (no LLM call)
    confidence >= 60            -> CB4 answer (assistant_service), LLM-failure
                                    falls back to the top KB answer directly
    40 <= confidence < 60       -> clarification (top-3 KB questions, no LLM)
    confidence < 40             -> out-of-scope fallback + suggestions

`POST /voice` -- multipart audio -> faster-whisper transcript (text only;
the frontend sends the transcript through `/chat` itself, same two-step
flow as PathoIntern's VoiceChatbot).

Both endpoints are public and rate-limited per IP (10/min chat, 5/min
voice) via `app/core/rate_limit.py`.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.rate_limit import assistant_chat_limiter, assistant_voice_limiter, rate_limit_dependency
from app.services import assistant_kb, assistant_service, voice_transcribe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ConversationTurn(BaseModel):
    role: Literal["user", "bot"]
    content: str


class ChatRequest(BaseModel):
    query: str
    language: Optional[str] = None  # "en" | "fr" | None (defaults to "en")
    history: list[ConversationTurn] = []


class Source(BaseModel):
    question: str
    category: str
    score: float


class ChatResponse(BaseModel):
    response: str
    language: str
    confidence: float
    sources: list[Source] = []
    latency: float
    used_llm: bool
    suggested_questions: list[str] = []
    clarification_needed: bool = False
    clarification_options: list[str] = []
    redirect_to_qa: bool = False


def _norm_language(language: Optional[str]) -> str:
    return language if language in ("en", "fr") else "en"


def _to_sources(raw: list[dict]) -> list[Source]:
    return [Source(question=s["question"], category=s["category"], score=s["score"]) for s in raw]


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(body: ChatRequest, _: None = Depends(rate_limit_dependency(assistant_chat_limiter))):
    start = time.perf_counter()
    language = _norm_language(body.language)

    def elapsed() -> float:
        return round(time.perf_counter() - start, 2)

    # 1. Medication-intent gate -- BEFORE retrieval, no KB lookup, no LLM call.
    if assistant_kb.is_medication_intent(body.query):
        redirect_msg = assistant_kb.MED_REDIRECT_FR if language == "fr" else assistant_kb.MED_REDIRECT_EN
        return ChatResponse(
            response=redirect_msg,
            language=language,
            confidence=0.0,
            sources=[],
            latency=elapsed(),
            used_llm=False,
            redirect_to_qa=True,
        )

    # 2. Fuzzy KB retrieval.
    context, sources, confidence = assistant_kb.retrieve(body.query, top_k=5)

    # 3. Map frontend history ("bot" role) to LLM history ("assistant" role),
    # capped at the last 10 turns (5 exchanges).
    llm_history = [
        {"role": "assistant" if t.role == "bot" else "user", "content": t.content}
        for t in body.history[-10:]
    ]

    # ── Zone A: confidence >= 60 -- LLM answer path ─────────────────────────
    if confidence >= assistant_kb.HIGH_CONFIDENCE_THRESHOLD:
        suggestions = [s["question"] for s in sources[1:4]]
        try:
            response_text = await assistant_service.generate_answer(
                query=body.query, context=context, language=language, history=llm_history,
            )
            return ChatResponse(
                response=response_text,
                language=language,
                confidence=round(confidence, 2),
                sources=_to_sources(sources[:3]),
                latency=elapsed(),
                used_llm=True,
                suggested_questions=suggestions,
            )
        except Exception as exc:  # noqa: BLE001 -- degrade to the top KB answer, never a 500
            logger.warning(
                "Assistant CB4 unavailable (%s: %s); serving top KB answer directly.",
                type(exc).__name__, exc,
            )
            direct_answer = sources[0]["answer"] if sources else (
                assistant_kb.FALLBACK_FR if language == "fr" else assistant_kb.FALLBACK_EN
            )
            return ChatResponse(
                response=direct_answer,
                language=language,
                confidence=round(confidence, 2),
                sources=_to_sources(sources[:3]),
                latency=elapsed(),
                used_llm=False,
                suggested_questions=suggestions,
            )

    # ── Zone B: 40 <= confidence < 60 -- clarification ──────────────────────
    if confidence >= assistant_kb.CLARIFICATION_THRESHOLD:
        clarification_msg = (
            assistant_kb.CLARIFICATION_PROMPT_FR if language == "fr" else assistant_kb.CLARIFICATION_PROMPT_EN
        )
        options = [s["question"] for s in sources[:3]]
        return ChatResponse(
            response=clarification_msg,
            language=language,
            confidence=round(confidence, 2),
            sources=_to_sources(sources[:3]),
            latency=elapsed(),
            used_llm=False,
            clarification_needed=True,
            clarification_options=options,
        )

    # ── Zone C: confidence < 40 -- out of scope ──────────────────────────────
    fallback = assistant_kb.FALLBACK_FR if language == "fr" else assistant_kb.FALLBACK_EN
    suggestions = [s["question"] for s in sources[:3]]
    return ChatResponse(
        response=fallback,
        language=language,
        confidence=round(confidence, 2),
        sources=_to_sources(sources[:3]),
        latency=elapsed(),
        used_llm=False,
        suggested_questions=suggestions,
    )


# ---------------------------------------------------------------------------
# POST /voice
# ---------------------------------------------------------------------------

@router.post("/voice")
async def assistant_voice(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    _: None = Depends(rate_limit_dependency(assistant_voice_limiter)),
):
    if not audio:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NO_AUDIO", "message": "No audio file provided."}},
        )

    temp_file_path: Optional[str] = None
    try:
        suffix = (os.path.splitext(audio.filename)[1] if audio.filename else ".wav") or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            temp_file_path = tmp.name

        lang = language if language in ("en", "fr") else "en"
        text = voice_transcribe.transcribe(temp_file_path, language=lang)
        return {"text": text}

    except Exception as exc:  # noqa: BLE001 -- clean error envelope, never a raw 500 traceback
        logger.warning("Assistant voice transcription failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "TRANSCRIBE_FAILED", "message": "Could not transcribe that audio."}},
        ) from exc

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
