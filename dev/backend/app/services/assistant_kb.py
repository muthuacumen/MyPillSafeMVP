"""MyPillSafe Assistant -- knowledge-base loading + fuzzy retrieval (Phase 5).

The floating "MyPillSafe Assistant" widget is a PUBLIC, no-auth project
EXPLAINER -- it answers questions about how MyPillSafe works, its safety
design, the research behind it, and the team, from the curated
`app/data/assistant_kb.json` (already authored by the SA; never edit its
content here). It never answers medication-specific questions -- those
belong to the authenticated, DIN-scoped `/api/v1/qa/chat` (BB3 + CB4).

Retrieval mirrors PathoIntern's `kb_service.py` confidence-zone design
(`documentation/integration/phase5_content_pack.md` / PathoIntern's
`backend/app/api/chatbot.py`), but swaps pgvector cosine similarity for
`rapidfuzz.fuzz.token_set_ratio` (0-100) against each entry's `question` +
`question_fr` (best of the two) -- there is no embedding store here, and
english/french aliasing on the same entries makes fuzzy text matching a
reasonable, dependency-light substitute for this small, hand-curated KB.

Confidence zones (0-100 raw fuzzy score, calibrated for this KB):
    >= HIGH_CONFIDENCE_THRESHOLD (60)  -> LLM answer path
    >= CLARIFICATION_THRESHOLD (40)    -> clarification (top-3 KB questions)
    <  CLARIFICATION_THRESHOLD         -> out-of-scope fallback

All EN/FR strings below are transcribed VERBATIM from
`documentation/integration/phase5_content_pack.md` section 8 -- do not
paraphrase or add statistics not present in that pack.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "assistant_kb.json"

HIGH_CONFIDENCE_THRESHOLD = 60.0
CLARIFICATION_THRESHOLD = 40.0

# --- content pack §8 strings, verbatim -----------------------------------

MED_REDIRECT_EN = (
    "That sounds like a question about a medication. I'm only the project guide — for "
    "medication questions, please use **Ask about my medication** inside the app (it answers "
    "from official Health Canada monographs, with citations), and always confirm with your "
    "pharmacist."
)
MED_REDIRECT_FR = (
    "Cela ressemble à une question sur un médicament. Je ne suis que le guide du projet — pour "
    "les questions sur les médicaments, utilisez **Poser une question sur mon médicament** dans "
    "l'application (réponses tirées des monographies officielles de Santé Canada, avec "
    "citations), et confirmez toujours avec votre pharmacien."
)

FALLBACK_EN = (
    "I'm not sure that's something I know — I can answer questions about the MyPillSafe "
    "project: how it works, its safety design, the research, and the team. Try one of the "
    "suggestions below."
)
FALLBACK_FR = (
    "Je ne suis pas certain de pouvoir répondre à cela — je peux répondre aux questions sur le "
    "projet MyPillSafe : son fonctionnement, sa conception axée sur la sécurité, la recherche et "
    "l'équipe. Essayez l'une des suggestions ci-dessous."
)

CLARIFICATION_PROMPT_EN = "I found a few related topics — which one did you mean?"
CLARIFICATION_PROMPT_FR = "J'ai trouvé quelques sujets connexes — lequel vouliez-vous dire ?"


# --- medication-intent gate ------------------------------------------------
# Runs BEFORE retrieval -- a hit here short-circuits straight to the
# med-redirect string with no KB lookup and no LLM call. Deliberately
# keyword-broad (safety-biased: an occasional false-positive redirect is a
# cheap extra click; a false negative would let a medication-specific
# question reach the KB/LLM path, which this assistant must never answer).
# The CB4 system prompt (assistant_service.py) enforces the same rule as a
# second layer, in case a medication question is phrased in a way that
# slips past this heuristic.

_MED_KEYWORD_PATTERNS = [
    r"\bdose\b", r"\bdosage\b", r"\bdoses\b",
    r"\bmg\b", r"\bmilligram", r"\bmcg\b",
    r"\btake\b", r"\btaking\b", r"\bprendre\b",
    r"\binteraction", r"\binteract\b",
    r"\bside[\s-]?effect", r"\beffet secondaire",
    r"\bpregnan", r"\bgrossesse\b", r"\benceinte\b",
    r"\balcohol\b", r"\balcool\b",
]
_MED_KEYWORD_RE = re.compile("|".join(_MED_KEYWORD_PATTERNS), re.IGNORECASE)
# "looks like a drug name question" pattern, e.g. "can I take ibuprofen with warfarin?"
_DRUG_QUESTION_RE = re.compile(
    r"\bcan i take\b|\bpuis[- ]je prendre\b|\bshould i take\b|\bis it safe to take\b",
    re.IGNORECASE,
)


def is_medication_intent(query: str) -> bool:
    """True when `query` looks like it's asking about a specific medication
    (dose, interaction, side effect, "can I take X") rather than about the
    MyPillSafe project itself."""
    if not query:
        return False
    return bool(_MED_KEYWORD_RE.search(query) or _DRUG_QUESTION_RE.search(query))


# --- KB loading + retrieval -------------------------------------------------


def _load_entries() -> list[dict[str, Any]]:
    with KB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["entries"]


_ENTRIES: list[dict[str, Any]] = _load_entries()


def retrieve(query: str, top_k: int = 5) -> tuple[str, list[dict[str, Any]], float]:
    """Fuzzy-match `query` against every KB entry's question/question_fr.

    Returns (context, sources, confidence):
      - context: the top-3 entries packed as "Q: ...\\nA: ..." blocks, for
        the LLM prompt.
      - sources: up to `top_k` entries as
        {question, category, score (0-100), answer}, best-first. `answer`
        is used internally (top-KB-answer fallback) and stripped before the
        API response.
      - confidence: the top entry's fuzzy score (0-100), or 0.0 if the KB
        is empty.
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in _ENTRIES:
        score_en = fuzz.token_set_ratio(query, entry.get("question", ""))
        score_fr = fuzz.token_set_ratio(query, entry.get("question_fr", ""))
        scored.append((max(score_en, score_fr), entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = scored[:top_k]

    sources = [
        {
            "question": entry["question"],
            "category": entry["category"],
            "score": round(score, 2),
            "answer": entry["answer"],
        }
        for score, entry in top
    ]
    confidence = sources[0]["score"] if sources else 0.0
    context = "\n\n".join(f"Q: {s['question']}\nA: {s['answer']}" for s in sources[:3])
    return context, sources, confidence
