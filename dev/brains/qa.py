"""dev/brains/qa.py -- BB3 Q&A "context mode" support for the sidecar
(Phase 4 of the app x brains integration).

Per the ADR 2026-07-14 decision ("the answer-to-user LLM generation is CB4's
job, not BB3's local 7B" -- F9-11 celecoxib), BB3's local-7B generation
(`bb3.engine.BB3Engine.chat()`) stays the offline fallback + eval harness
only. The production path needs BB3's resolver -> short-circuit ->
enumeration -> retrieval -> dosing-gate -> packing control flow WITHOUT
generating an answer or requiring Ollama, so the app backend's `cb4_service`
(a cloud Claude model) can generate instead.

This module mirrors `BB3Engine.chat()` (engine.py lines ~189-253) FIELD FOR
FIELD, importing only from the frozen BB3 package (never editing it):
`bb3.resolver`, `bb3.enumerate`, `bb3.retrieve`, `bb3.store`, and the
module-level constants + a few `BB3Engine` @staticmethods from `bb3.engine`.
Short-circuit statuses (confirm/pick_list/not_found/no_entity/enumeration/
refused_dosing/empty-retrieval abstention) return response dicts identical
to what `chat()` would return (minus latency_s, which is a fresh timer here).
When generation would happen, `chat_context()` returns `status:
"context_ready"` with the packed cited context instead of calling an LLM.

Two things this module deliberately does NOT do, per the Phase 4 spec:
  - never instantiate `BB3Engine` in context mode (its constructor requires
    `ollama_up()`, which context mode must not depend on);
  - never turn rerank on (BB3Engine's shipped default is rerank=False --
    CONTRACT.md Sec6's F8 A/B verdict -- and this module has no rerank path
    at all).

`mode="full"` (the offline fallback, used when no cloud LLM_API_KEY is
configured app-side) DOES need a real `BB3Engine` + a running Ollama --
`get_full_engine()` below is a lazy cached singleton for that path only.
"""
from __future__ import annotations

import re
import time
from typing import Any

import config  # noqa: F401  -- side effect: inserts BB3_ROOT onto sys.path

# --- Import the frozen BB3 package defensively ------------------------------
# Same discipline as app.py's imb1/sb2 imports: a failure here must never
# crash the service -- /health has to keep responding and report the error.

_import_error: str | None = None

try:
    from bb3 import enumerate as enumerate_mod  # noqa: E402
    from bb3 import guards as guards_mod  # noqa: E402
    from bb3 import resolver as resolver_mod  # noqa: E402
    from bb3 import retrieve as retrieve_mod  # noqa: E402
    from bb3 import store as store_mod  # noqa: E402
    from bb3.engine import (  # noqa: E402
        BB3Engine,
        DOSING_INTENT_RE,
        DOSING_REFUSAL,
        PACK_CAP,
        PACK_PER_PARENT,
        PACK_TOP_N,
        STANDARD_DISCLAIMER,
        TIER_DISCLAIMERS,
        ollama_up as _ollama_up,
    )
except Exception as exc:  # pragma: no cover - defensive, exercised by /health
    enumerate_mod = guards_mod = resolver_mod = retrieve_mod = store_mod = None  # type: ignore[assignment]
    BB3Engine = None  # type: ignore[assignment]
    DOSING_INTENT_RE = None  # type: ignore[assignment]
    DOSING_REFUSAL = ""
    PACK_CAP = PACK_PER_PARENT = PACK_TOP_N = 0
    STANDARD_DISCLAIMER = ""
    TIER_DISCLAIMERS = {}

    def _ollama_up() -> bool:  # type: ignore[misc]
        return False

    _import_error = repr(exc)


def bb3_import_error() -> str | None:
    return _import_error


def ollama_up() -> bool:
    return _ollama_up()


# --- one cached readonly store connection (module singleton, per spec) -----

_con: Any = None


def get_connection():
    """Lazily open (once) BB3's readonly SQLite+memmap store connection --
    `bb3.store.connect(readonly=True)`, reused across every /qa/chat call in
    this process."""
    global _con
    if _con is None:
        if store_mod is None:
            raise RuntimeError(_import_error or "bb3.store not importable")
        _con = store_mod.connect(readonly=True)
    return _con


def store_ok() -> "bool | str":
    """For /health: True if the store can be opened, else an error string."""
    try:
        get_connection()
        return True
    except Exception as exc:
        return repr(exc)


def bb3_ok() -> "bool | str":
    """For /health: True if the bb3 package imports AND its store opens,
    else the first error encountered (import errors take priority since a
    store-open attempt would just fail the same way again)."""
    if _import_error is not None:
        return _import_error
    return store_ok()


# --- verbatim-ported tiny helpers -------------------------------------------
# BB3Engine._base_response / _disclaimer / _describe / _priority (engine.py
# lines ~130-186) are a few lines each -- ported faithfully here since
# context mode never instantiates BB3Engine. BB3Engine._source_tag /
# _tier_of / _resolution_summary are @staticmethods and are reused directly
# via the class (no instantiation needed for those).

def _base_response(status: str, resolution: dict, t0: float, **extra: Any) -> dict:
    base = {
        "status": status,
        "resolution": BB3Engine._resolution_summary(resolution),
        "abstained": True,
        "answer": "",
        "sources": [],
        "tier": "none",
        "disclaimer": STANDARD_DISCLAIMER,
        "cited_tags": [],
        "priority": 0.0,
        "latency_s": round(time.time() - t0, 2),
        "refused_dosing": False,
    }
    base.update(extra)
    return base


def _disclaimer(tier: str) -> str:
    extra = TIER_DISCLAIMERS.get(tier, "")
    return (extra + " " + STANDARD_DISCLAIMER).strip()


def _describe(results: list[dict]) -> list[dict]:
    return [
        {
            "tag": BB3Engine._source_tag(r),
            "section": r.get("section"),
            "source": r.get("source"),
            "match_status": r.get("match_status"),
            "score": r.get("score"),
            "rerank_score": r.get("rerank_score"),
        }
        for r in results
    ]


def _priority(results: list[dict], cited: list[str], abstained: bool, guard_flags: dict) -> float:
    """Soft review-priority (verbatim base logic + guard-flag bumps, F10/Sec7).
    Not currently emitted by context mode itself (generation -- and hence
    guard_flags -- happens app-side, in cb4_service.py, which ports this same
    formula); kept here per spec so the sidecar module carries its own
    faithful copy alongside the other three helpers."""
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


def _retrieve(question: str, din_set: set, con) -> list[dict]:
    """Verbatim port of BB3Engine._retrieve's rerank=False branch (the only
    branch this module has -- rerank is never turned on here)."""
    results = retrieve_mod.retrieve(question, din_set, con=con, top_n=PACK_TOP_N)
    return results[:PACK_TOP_N]


# --- main entry: context mode ------------------------------------------------

def chat_context(message: str, din: str | None = None, confirmed_name: str | None = None) -> dict:
    """Mirrors `BB3Engine.chat()`'s pre-generation control flow field for
    field (engine.py lines ~189-253), without requiring Ollama and without
    instantiating BB3Engine. Short-circuit statuses return dicts identical
    to what `chat()` would return (minus latency_s). When generation would
    happen, returns `status: "context_ready"` with the packed cited context
    for the app's cb4_service to hand to Claude instead."""
    if BB3Engine is None:
        raise RuntimeError(_import_error or "bb3 package not importable")

    con = get_connection()
    t0 = time.time()

    if din is not None:
        resolution = resolver_mod.resolve_din(din, con)
    else:
        resolution = resolver_mod.resolve(message, con, confirmed_name=confirmed_name)

    status = resolution["status"]
    if status == "confirm":
        c = resolution["candidates"][0]
        answer = f"Did you mean -- {c['name']}? Please confirm."
        return _base_response("confirm", resolution, t0, answer=answer)
    if status == "pick_list":
        names = ", ".join(c["name"] for c in resolution["candidates"])
        answer = f"I found more than one match: {names}. Which did you mean?"
        return _base_response("pick_list", resolution, t0, answer=answer)
    if status == "not_found":
        answer = ("I couldn't find that medication in the Canadian formulary -- please "
                  "check the spelling, give the ingredient name, or the DIN from the package.")
        return _base_response("not_found", resolution, t0, answer=answer)
    if status == "no_entity":
        answer = ("I answer questions about specific medications. Name the medication, "
                  "or pick one from your profile.")
        return _base_response("no_entity", resolution, t0, answer=answer)

    # status == "resolved" -- enumeration intent short-circuits (Sec6, no LLM)
    enum_result = enumerate_mod.run(message, con)
    if enum_result is not None:
        return _base_response("enumeration", resolution, t0, abstained=False,
                               answer=enum_result["text"], tier="enumeration")

    din_set = resolution["din_set"]
    results = _retrieve(message, din_set, con)
    if not results:
        return _base_response(
            "answered", resolution, t0,
            answer="I don't have that information in my reference documents.")

    tier = BB3Engine._tier_of(results)
    all_openfda = all(r.get("source") == "openfda_ai" for r in results)
    if all_openfda and DOSING_INTENT_RE.search(message):
        return _base_response(
            "refused_dosing", resolution, t0, answer=DOSING_REFUSAL,
            sources=_describe(results), tier=tier, disclaimer=_disclaimer(tier),
            refused_dosing=True)

    # ---- generation would happen here in chat() -- instead, pack the cited
    # context and hand it back (verbatim packing loop, engine.py ~236-246) --
    texts = [r.get("section_text", "") or "" for r in results]
    blocks: list[str] = []
    used = 0
    for r, t in zip(results, texts):
        body = t[:PACK_PER_PARENT] if PACK_PER_PARENT else t
        remaining = PACK_CAP - used
        if remaining <= 0:
            break
        body = body[:remaining]
        blocks.append(f"{BB3Engine._source_tag(r)} (section: {r.get('section', '?')})\n{body}")
        used += len(body) + 2

    offered = sorted({BB3Engine._source_tag(r) for r in results})
    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "sources_used": {"type": "array", "items": {"type": "string", "enum": offered}},
            "abstained": {"type": "boolean"},
        },
        "required": ["answer", "sources_used", "abstained"],
    }
    entity_names = [e["name"] for e in resolution["entities"]]

    return {
        "status": "context_ready",
        "resolution": BB3Engine._resolution_summary(resolution),
        "sources": _describe(results),
        "tier": tier,
        "disclaimer": _disclaimer(tier),
        "offered_tags": offered,
        "packed_sources": "\n\n".join(blocks),
        "question": message,
        "schema": schema,
        "entity_names": entity_names,
    }


# --- guard checks (single-shot; the app owns the retry protocol) -----------

# Header line of each packed block, produced verbatim by chat_context's packing loop
# (`f"{tag} (section: {section})\n{body}"`, blocks joined by "\n\n"). Kept next to the
# packer so the two never drift. Splitting on header positions (not blank lines) is robust
# to section_text that itself contains blank lines.
_PACK_HEADER_RE = re.compile(r"^\[(?:DIN|ING):[^\]]*\] \(section: ([^)]*)\)$", re.M)


def _parse_packed_sections(packed_context: str) -> list[tuple[str, str]]:
    """Reconstruct [(section, section_text), ...] from a packed_sources string -- the
    input the WP2.5 polarity guard needs. The app already holds packed_context, so this
    reuses it instead of a second large round-trip field."""
    if not packed_context:
        return []
    matches = list(_PACK_HEADER_RE.finditer(packed_context))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        section = m.group(1)
        start = m.end() + 1  # skip the newline after the header line
        end = matches[i + 1].start() if i + 1 < len(matches) else len(packed_context)
        out.append((section, packed_context[start:end].strip()))
    return out


def run_guards(answer: str, sources_used: list[str], abstained: bool, entity_names: list[str],
               question: str | None = None, packed_context: str | None = None) -> dict:
    """Runs BB3's single-shot post-generation guard checks (guards.py) on an
    already-generated answer. No retry logic here -- the app backend owns
    the retry protocol (cb4_service.py mirrors guards.check_and_fix).

    question + packed_context are optional (WP2.5): when both are supplied, the
    claim-source polarity guard runs against the reconstructed source sections
    (F9-11 celecoxib class). Omitting them preserves the pre-WP2.5 behaviour."""
    if guards_mod is None:
        raise RuntimeError(_import_error or "bb3.guards not importable")
    parsed = {"answer": answer, "sources_used": sources_used, "abstained": abstained}
    cited_dins = guards_mod.cited_dins_of(parsed)
    entity_violation = guards_mod.entity_guard_violation(answer, entity_names, cited_dins)
    ingredient_violation = guards_mod.ingredient_consistency_violation(answer, cited_dins)
    structural_inconsistency = guards_mod.abstention_consistency_violation(
        abstained, sources_used, answer)
    polarity_violation = None
    if question and packed_context:
        polarity_violation = guards_mod.polarity_contradiction_violation(
            question, answer, _parse_packed_sections(packed_context))
    return {
        "entity_violation": entity_violation,
        "ingredient_violation": ingredient_violation,
        "structural_inconsistency": structural_inconsistency,
        "polarity_violation": polarity_violation,
    }


# --- mode="full": lazy cached BB3Engine (offline fallback only) ------------

_engine: Any = None


def get_full_engine():
    """Lazy singleton `BB3Engine` for `mode="full"` (offline fallback) calls
    only. Requires Ollama up (BB3Engine.__init__ raises RuntimeError if not
    -- callers should check `ollama_up()` first for a clean 503, same as
    this function will raise if that check is skipped)."""
    global _engine
    if _engine is None:
        if BB3Engine is None:
            raise RuntimeError(_import_error or "bb3 package not importable")
        _engine = BB3Engine(con=get_connection())
    return _engine
