"""MyPillSafe Assistant -- CB4 answer generation for the public project
explainer widget (Phase 5).

Reuses the same lazily-constructed Anthropic client and `LLM_API_KEY` /
`LLM_MODEL` config as `cb4_service.py` (the ONE cloud call in the system --
see that module's docstring). This is a distinct, much smaller prompt: a
friendly-plain project explainer that answers strictly from the KB context
`assistant_kb.retrieve()` packs, never from outside knowledge, and never
answers medication-specific questions (that's `/api/v1/qa/chat`'s job).

`generate_answer()` raises on any failure (empty response, SDK/network
error) -- the caller (`routes/assistant.py`) catches and falls back to
serving the top KB answer directly with `used_llm: false`, mirroring
PathoIntern's fallback pattern and cb4_service's own None-on-failure
contract at the `_call_claude` seam.
"""
from __future__ import annotations

import logging

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.services import cb4_service

logger = logging.getLogger(__name__)

MAX_TOKENS = 500

SYSTEM_PROMPT_TEMPLATE = """You are the MyPillSafe Assistant -- a friendly project guide for MyPillSafe, \
a Conestoga College capstone medication-safety app. You are handed KNOWLEDGE BASE CONTEXT (a small set \
of curated Q&A entries about the project) and a user question.

Rules:
1. Answer ONLY using the KNOWLEDGE BASE CONTEXT provided below -- never outside knowledge, never guesses.
2. Your scope is explaining the MyPillSafe project ONLY: how it works, its safety design, the research \
behind it, and the team. You are not a medical tool.
3. If the user's question is actually about a specific medication -- a dose, an interaction, a side \
effect, whether they personally can take something -- do NOT answer it. Instead respond with exactly \
this sentence (translated into the requested language if needed): "That sounds like a question about a \
medication. I'm only the project guide — for medication questions, please use Ask about my medication \
inside the app (it answers from official Health Canada monographs, with citations), and always confirm \
with your pharmacist."
4. Answer in {language}.
5. Keep your answer to 180 words or fewer.
6. Never introduce statistics, numbers, or citations that are not present in the KNOWLEDGE BASE CONTEXT.
7. Friendly, plain-spoken tone. Be honest that MyPillSafe is a capstone research project providing \
decision-support only, when relevant -- never overstate its capabilities.

Respond with plain text only -- no JSON, no markdown headers."""


def _call_claude(client, system_prompt: str, context: str, question: str, history: list[dict]) -> str | None:
    """Synchronous Claude call (run off the event loop via run_in_threadpool).
    Returns the answer text, or None on any failure/empty response."""
    messages = list(history) + [
        {
            "role": "user",
            "content": f"KNOWLEDGE BASE CONTEXT:\n{context}\n\nUSER QUESTION: {question}",
        }
    ]
    try:
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )
    except Exception as exc:  # noqa: BLE001 -- any SDK/network failure degrades to the KB fallback
        logger.warning("Assistant CB4 call failed: %s", exc)
        return None

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    text = "".join(text_parts).strip()
    return text or None


async def generate_answer(query: str, context: str, language: str, history: list[dict]) -> str:
    """Generates the assistant's answer for a high-confidence KB match.

    Raises RuntimeError if no LLM_API_KEY is configured, or if the Claude
    call fails / returns empty -- the route catches this and falls back to
    the top KB answer directly.
    """
    client = cb4_service._get_client()
    if client is None:
        raise RuntimeError("assistant_service.generate_answer called with no LLM_API_KEY configured")

    language_name = "French" if language == "fr" else "English"
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language_name)

    answer = await run_in_threadpool(_call_claude, client, system_prompt, context, query, history)
    if not answer:
        raise RuntimeError("Assistant CB4 call returned no usable answer")
    return answer
