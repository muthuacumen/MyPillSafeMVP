"""CB4 -- the production voice for BB3 Q&A (Phase 4, app x brains
integration). Per the 2026-07-14 ADR ("the answer-to-user LLM generation is
CB4's job, not BB3's local 7B" -- F9-11 celecoxib: the local 7B inverted its
own cited contraindication), a cloud Claude model generates the user-facing
answer from BB3's pre-retrieved, DIN-scoped, packed context. BB3's
deterministic guards (entity / ingredient-consistency / structured
abstention) still run against CB4's output, via the sidecar's `/qa/guard`
endpoint -- this module owns the retry protocol (mirrors
`bb3.guards.check_and_fix`), the sidecar itself is single-shot only.

The Anthropic client is constructed lazily and ONLY when
`settings.LLM_API_KEY` is non-empty (`cb4_enabled()` -- the app route uses
this to decide context-mode/CB4 vs the sidecar's mode="full" local-7B
offline fallback). No cloud API keys live in the brains sidecar (SB2/BB3 are
local-only by design) -- this is the one and only cloud call in the system.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- lazy client -------------------------------------------------------------

_client: Any = None
_client_checked = False


def _get_client():
    global _client, _client_checked
    if not _client_checked:
        _client_checked = True
        if settings.LLM_API_KEY:
            import anthropic
            _client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
    return _client


def cb4_enabled() -> bool:
    """True when a cloud LLM_API_KEY is configured -- the app route uses
    this to pick context-mode+CB4 vs the sidecar's offline mode="full"."""
    return bool(settings.LLM_API_KEY)


# --- CB4 system prompt (fixed constant) --------------------------------------
# Carries the semantic rules of bb3.engine.PROMPT_TEMPLATE (rule numbers
# below map 1:1 onto that template) plus the language + polarity additions
# this session's spec calls for. Never edits the frozen BB3 package --
# BB3's own template stays untouched; this is the app-side CB4 equivalent.

SYSTEM_PROMPT_TEMPLATE = """You are MyPillSafe's medication-information assistant. You are handed \
pre-retrieved SOURCE SECTIONS (DIN-scoped Canadian product monographs or generated ingredient \
references) and a user question -- you have no independent knowledge of these products. Answer \
using ONLY the SOURCE SECTIONS given to you -- never outside knowledge, never guesses.

Rules:
1. If the sources do not contain the answer, set "answer" to exactly: "I don't have that \
information in my reference documents.", "sources_used" to [], and "abstained" to true. \
Otherwise set "abstained" to false. Do not speculate.
2. In "sources_used", list the tag of every source section your answer draws on (the [DIN:...] \
or [ING:...] label shown at the start of each section). An answer with substance must list at \
least one source; content without a supporting source must not be stated.
3. If EVERY source section is tagged [ING:...] (generated ingredient reference), never state a \
dose, amount, or frequency -- even if the user asks. Direct them to their pharmacist instead.
4. Be concise and plain-spoken; the user may be a senior. Short sentences.
5. Never diagnose, never tell the user whether to take or skip a medication -- describe what the \
reference documents say and tell them to confirm with a pharmacist or doctor.
6. Pay close attention to the POLARITY of every contraindication, warning, and allergy statement \
in the sources. If a source says a product should NOT be used, is contraindicated, or has a \
demonstrated allergic-type reaction to something, your answer must preserve that exact direction \
-- never assert or imply the opposite of what a cited source says.
7. Answer in {language}.

Respond via the given JSON schema."""

CAUTION_NOTE = ("\n\n[MyPillSafe note: this answer arrived without source citations and "
                "should be treated with extra caution.]")
SAFE_REFUSAL = "I couldn't produce a reliable answer for this -- please ask your pharmacist."
JSON_DEGENERACY_MSG = "Something went wrong generating this answer -- please try re-phrasing."
CONTRADICTION_REFUSAL = (
    "I can't confirm whether this medication is safe for you given that concern -- its "
    "monograph lists related contraindications or warnings, so please confirm with your "
    "pharmacist or doctor before taking it.")

GUARD_CHECK_TIMEOUT_SECONDS = 20.0

_DEFAULT_GUARD_FLAGS = {
    "json_degenerate_retried": False,
    "entity_guard_retried": False,
    "ingredient_consistency_retried": False,
    "polarity_contradiction_retried": False,
    "guard_refused": False,
    "structural_inconsistency": False,
}


# --- BB3Engine._priority, ported (app-side copy -- see qa.py's own port in --
# the sidecar; both exist because the backend never imports bb3 directly). --

def _priority(results: list[dict], cited: list[str], abstained: bool, guard_flags: dict) -> float:
    score = 0.0
    if not cited and not abstained:
        score += 60
    if results and all(r.get("source") == "openfda_ai" for r in results):
        score += 20
    n = len(results)
    score += max(0.0, (5 - n) * 4)
    if guard_flags.get("structural_inconsistency"):
        score += 30
    if guard_flags.get("guard_refused"):
        score += 100
    return round(min(score, 100.0), 1)


def _schema_for_api(schema: dict) -> dict:
    """The Claude structured-outputs API requires additionalProperties:
    false on every object -- add it without mutating the caller's schema
    dict (which came verbatim from the sidecar's context_ready payload)."""
    out = dict(schema)
    out["additionalProperties"] = False
    return out


def _call_claude(client, system_prompt: str, packed_sources: str, question: str, schema: dict) -> dict | None:
    """Synchronous Claude call (run off the event loop via run_in_threadpool
    by every async caller below). Returns the parsed {"answer", "sources_used",
    "abstained"} dict, or None on any parse failure / empty response --
    mirrors bb3/engine.py's call_llm() closure's None-on-failure contract."""
    user_content = f"SOURCE SECTIONS:\n{packed_sources}\n\nUSER QUESTION: {question}"
    try:
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            output_config={"format": {"type": "json_schema", "schema": _schema_for_api(schema)}},
        )
    except Exception as exc:  # noqa: BLE001 -- any SDK/network failure degrades to a retry, not a crash
        logger.warning("CB4 (Claude) call failed: %s", exc)
        return None

    text = None
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text = block.text
            break
    if not text:
        return None

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    return {
        "answer": str(parsed.get("answer", "")).strip(),
        "sources_used": [t for t in (parsed.get("sources_used") or []) if isinstance(t, str)],
        "abstained": bool(parsed.get("abstained", False)),
    }


async def _check_guards(answer: str, sources_used: list[str], abstained: bool, entity_names: list[str],
                        question: str | None = None, packed_context: str | None = None) -> dict:
    """POSTs the sidecar's /qa/guard (single-shot BB3 guard checks). Raises
    on failure -- guard checks are safety-critical and must never be
    silently skipped; the route catches and returns a clean error envelope.

    question + packed_context (WP2.5) enable the claim-source polarity guard."""
    async with httpx.AsyncClient(timeout=GUARD_CHECK_TIMEOUT_SECONDS) as http_client:
        response = await http_client.post(
            f"{settings.BRAINS_SERVICE_URL}/qa/guard",
            json={
                "answer": answer,
                "sources_used": sources_used,
                "abstained": abstained,
                "entity_names": entity_names,
                "question": question,
                "packed_context": packed_context,
            },
        )
        response.raise_for_status()
        return response.json()


def _empty(parsed: dict | None) -> bool:
    return parsed is None or not (parsed.get("answer") or "").strip()


def _refused_response(flags: dict, results: list[dict], answer: str = SAFE_REFUSAL) -> dict:
    return {
        "status": "guard_refused",
        "abstained": True,
        "answer": answer,
        "cited_tags": [],
        "priority": _priority(results, [], True, flags),
        "guard_flags": flags,
    }


async def answer_question(
    packed_sources: str,
    question: str,
    offered_tags: list[str],
    schema: dict,
    entity_names: list[str],
    sources: list[dict],
    language: str = "English",
) -> dict:
    """Generates CB4's answer for a `context_ready` payload from the sidecar,
    then runs BB3's guard protocol against it (mirrors
    `bb3.guards.check_and_fix` -- JSON-degeneracy retry, then one corrective
    retry each for entity-guard / ingredient-consistency violations, then a
    hard `guard_refused` if the retry still fails the same check).

    Returns a dict shaped like a slice of BB3's own response: {status
    ("answered" | "guard_refused"), abstained, answer, cited_tags, priority,
    guard_flags}. The caller (routes/qa.py) assembles the rest of BB3's
    output shape (resolution/sources/tier/disclaimer come from the sidecar's
    context_ready payload verbatim) and adds voice="cb4" + model.
    """
    client = _get_client()
    if client is None:
        raise RuntimeError("cb4_service.answer_question called with no LLM_API_KEY configured")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language or "English")
    flags = dict(_DEFAULT_GUARD_FLAGS)

    async def generate(corrective: str | None) -> dict | None:
        prompt = question if not corrective else f"{question}\n\n{corrective}"
        return await run_in_threadpool(_call_claude, client, system_prompt, packed_sources, prompt, schema)

    parsed = await generate(None)

    if _empty(parsed):
        flags["json_degenerate_retried"] = True
        parsed = await generate(None)
        if _empty(parsed):
            return {
                "status": "answered",
                "abstained": True,
                "answer": JSON_DEGENERACY_MSG,
                "cited_tags": [],
                "priority": _priority(sources, [], True, flags),
                "guard_flags": flags,
            }

    parsed["sources_used"] = [t for t in parsed["sources_used"] if t in offered_tags]

    # Guard key / corrective / hard-refusal message per violation kind. Polarity (WP2.5,
    # F9-11 celecoxib) gets its own corrective + CONTRADICTION_REFUSAL; mirrors
    # bb3.guards.check_and_fix.
    def _corrective(kind: str, offender: str) -> str:
        if kind == "polarity":
            return (f"Your previous draft affirmed that the medication is safe with respect to "
                    f"'{offender}', but a CONTRAINDICATIONS or WARNINGS section in your sources "
                    f"names '{offender}'. Do NOT tell the user it is safe or that they can take "
                    f"it. State what the contraindication/warning says and tell them to confirm "
                    f"with their pharmacist or doctor. Never give a yes/no safety verdict.")
        return (f"Your previous draft mentioned {offender}, which is not among the "
                f"user's medication or your sources -- answer strictly about "
                f"{', '.join(entity_names) or 'the cited sources'}.")

    guard_loop = (
        ("entity_guard_retried", "entity", "entity_violation", SAFE_REFUSAL),
        ("ingredient_consistency_retried", "ingredient", "ingredient_violation", SAFE_REFUSAL),
        ("polarity_contradiction_retried", "polarity", "polarity_violation", CONTRADICTION_REFUSAL),
    )
    for flag_name, kind, result_key, refusal in guard_loop:
        guard_result = await _check_guards(
            parsed["answer"], parsed["sources_used"], parsed["abstained"], entity_names,
            question, packed_sources)
        offender = guard_result.get(result_key)
        if not offender:
            continue

        flags[flag_name] = True
        retried = await generate(_corrective(kind, offender))
        if _empty(retried):
            flags["guard_refused"] = True
            return _refused_response(flags, sources, refusal)

        retried["sources_used"] = [t for t in retried["sources_used"] if t in offered_tags]
        recheck = await _check_guards(
            retried["answer"], retried["sources_used"], retried["abstained"], entity_names,
            question, packed_sources)
        if recheck.get(result_key):
            flags["guard_refused"] = True
            return _refused_response(flags, sources, refusal)

        parsed = retried

    # Structural abstention check on the final parsed answer -- flags but
    # never retries (same as guards.check_and_fix / BB3Engine.chat()).
    final_guard = await _check_guards(
        parsed["answer"], parsed["sources_used"], parsed["abstained"], entity_names,
        question, packed_sources)
    if final_guard.get("structural_inconsistency"):
        flags["structural_inconsistency"] = True

    answer = parsed["answer"]
    abstained = parsed["abstained"]
    cited = parsed["sources_used"]
    # F9-04: a substantive but UNCITED answer mislabeled abstained=true is not really an
    # abstention -- relabel it so it earns the caution note (parity with engine.py).
    if abstained and not cited and answer.strip() and "don't have that information" not in answer.lower():
        abstained = False
    if not cited and not abstained:
        answer += CAUTION_NOTE

    return {
        "status": "answered",
        "abstained": abstained,
        "answer": answer,
        "cited_tags": cited,
        "priority": _priority(sources, cited, abstained, flags),
        "guard_flags": flags,
    }
