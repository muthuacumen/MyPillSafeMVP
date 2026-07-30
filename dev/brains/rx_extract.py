"""Rx label -> structured medication PROPOSALS, via the local Ollama
qwen2.5:7b-instruct (FixbyOPUS3 Task A1).

Same architectural place as `/ocr/prescription`: the heavy/model-bound work
lives on the ML tier (this sidecar's host), never on the droplet. Unlike
`/ocr/prescription` this needs no subprocess -- Ollama is already its own
process, so this module only speaks HTTP to it (stdlib `urllib`, no new
sidecar dependency, and deliberately nothing from `imb1`/`sb2`/`bb3` so the
backend's test venv can import and exercise this module directly).

THREE OPS RULES ARE LOAD-BEARING HERE (all measured on this project):

  1. `num_ctx` is ALWAYS passed explicitly. Ollama's default is 4,096 and it
     truncates the prompt SILENTLY -- a long OCR dump loses its tail and the
     model then "misses" medications that were in fact never shown to it.
  2. `temperature: 0` + `format: "json"` -- this is an extraction task with
     one right answer, not a generation task.
  3. `keep_alive: "10m"` -- releases VRAM when idle so the model can coexist
     with a live pill analysis (measured peak 7,374/8,188 MiB together). A
     cold reload costs ~7.5 s, which is acceptable inside a 15-20 s OCR flow.

What this module deliberately does NOT do: derive reminder times. The model
returns `explicit_times` -- clock times LITERALLY PRINTED on the label -- and
nothing else. Reminder times are computed server-side by the backend's
`rx_guardrails` from `frequency_type`, deterministically. That is a direct
consequence of the 2026-07-28 measurement: qwen2.5:7b's single miss on the
24-label probe was not extraction, it was time-slot derivation (it mapped a
French BID label to 08:00+13:00 instead of 08:00+18:00). Removing derivation
from the model turns that weakness into a structural non-issue.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"

RX_MODEL = os.environ.get("RX_LLM_MODEL", "qwen2.5:7b-instruct")

# Total wall-clock budget for one /rx/extract call, corrective retry
# INCLUDED (spec §3: "60 s cap"). The retry only runs if enough budget is
# left to have a real chance -- a 2 s retry would just manufacture a
# different failure.
TOTAL_BUDGET_SECONDS = 60.0
MIN_RETRY_BUDGET_SECONDS = 12.0

NUM_CTX = 8192
KEEP_ALIVE = "10m"

# Bound the blast radius of a pathological label (or a model that starts
# repeating itself): a real Canadian label carries a handful of medications.
MAX_MEDICATIONS = 20

FREQUENCY_ENUM = (
    "ONCE_DAILY", "BID", "TID", "QID", "BEDTIME", "WITH_MEALS",
    "PRN", "WEEKLY", "EVERY_N_HOURS", "TAPER", "UNKNOWN",
)

# Derived from the PROMPT constant in
# `documentation/deployment/redteam_llm_extraction.py`, which produced the
# measured 2026-07-28 numbers (12/12 originals, 11/12 held-out, 49/50
# fields, 0 safety events). Modified ONLY as spec §3 permits:
#   * the slot->time derivation block is GONE (the backend derives);
#   * `specific_times` -> `explicit_times`, restricted to clock times that
#     are literally printed on the label;
#   * an explicit at-most-20-medications cap.
# Everything else is byte-for-byte the measured prompt -- do not "improve"
# the rest without re-running the harness.
PROMPT = """You extract structured medication data from the raw OCR text of a Canadian pharmacy prescription label.

Return ONLY a JSON object: {"medications": [...]} -- one entry per DISTINCT medication actually present on the label. Output at most 20 medications.

Each entry has exactly these fields:
- "drug_name": string, the medication name including strength as printed (e.g. "APO-METFORMIN 500 MG")
- "dosage": string strength as printed (e.g. "500 mg") or null if no strength is printed
- "frequency_type": exactly one of these, using the plain meaning given here:
    ONCE_DAILY (once a day), BID (twice a day), TID (three times a day), QID (four times a day),
    BEDTIME (once a day, at night or bedtime), WITH_MEALS (with each meal),
    PRN (only as needed), WEEKLY (once a week),
    EVERY_N_HOURS (a fixed hourly interval, e.g. "every 8 hours"),
    TAPER (a stepped dose that changes over days, e.g. "4 tablets daily for 3 days, then 3 tablets daily for 3 days"),
    UNKNOWN
- "explicit_times": array of 24h "HH:MM" clock times that are LITERALLY PRINTED on the label (e.g. a label reading "8:00 PM" -> "20:00"). If the label prints no clock time, use []. Do NOT derive times from frequency words like "twice daily" or "at bedtime" -- the app computes those itself.
- "with_food": boolean

Hard rules:
- NEVER invent a medication, strength, or time that is not on the label.
- Pharmacy names, addresses, phone numbers, doctors, patient names, quantities, refills, DINs, and warning/counselling lines are NOT medications.
- If unsure of any field, use null / UNKNOWN / [] rather than guessing.
- The label may be in French; extract the same fields.

LABEL TEXT:
"""

_RETRY_INSTRUCTION = (
    "Your previous reply was not a valid JSON object. Reply again with ONLY "
    'the JSON object {"medications": [...]} and no other text, no markdown, '
    "no code fences."
)


class RxExtractError(Exception):
    """Typed failure. `code` is what the HTTP layer surfaces so the backend
    can tell "the model said there are no medications" (a 200 with an empty
    list) apart from "the model never ran" (a 503) -- honest degradation,
    never a fabricated prescription."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# --- Ollama plumbing --------------------------------------------------------

def _post_chat(messages: list[dict], timeout: float) -> str:
    body = json.dumps({
        "model": RX_MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        # num_ctx explicit -- see rule 1 in the module docstring.
        "options": {"temperature": 0, "num_ctx": NUM_CTX},
        "keep_alive": KEEP_ALIVE,
    }).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_CHAT_URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RxExtractError(
            "OLLAMA_HTTP_ERROR", f"Ollama returned HTTP {exc.code} from {OLLAMA_CHAT_URL}"
        ) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RxExtractError(
            "OLLAMA_UNREACHABLE", f"Ollama is not reachable at {OLLAMA_CHAT_URL}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RxExtractError(
            "OLLAMA_BAD_ENVELOPE", f"Ollama returned a non-JSON envelope: {exc}"
        ) from exc

    content = (payload.get("message") or {}).get("content")
    if not isinstance(content, str):
        raise RxExtractError(
            "OLLAMA_BAD_ENVELOPE", "Ollama response has no message.content string"
        )
    return content


def _extract_json_object(raw: str) -> dict:
    """Same tolerant unwrapping the measurement harness uses (fences, prose
    either side) -- kept identical so the service and the harness can never
    disagree about what counts as parseable model output."""
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model output JSON is not an object")
    return parsed


def _coerce_medications(parsed: dict) -> list[dict]:
    """Shape-only normalization. NOT a safety layer -- the real guards
    (catalog cross-check, no-invention, schema, no-silent-defaults,
    conflict) are the backend's `rx_guardrails`, deterministic and applied
    to BOTH proposers. This only makes the payload well-typed."""
    raw_meds = parsed.get("medications")
    if not isinstance(raw_meds, list):
        raise ValueError("model output has no 'medications' array")

    medications: list[dict] = []
    for item in raw_meds[:MAX_MEDICATIONS]:
        if not isinstance(item, dict):
            continue
        name = item.get("drug_name")
        if not isinstance(name, str) or not name.strip():
            continue
        dosage = item.get("dosage")
        frequency = item.get("frequency_type")
        times = item.get("explicit_times")
        medications.append({
            "drug_name": name.strip(),
            "dosage": dosage.strip() if isinstance(dosage, str) and dosage.strip() else None,
            "frequency_type": frequency if frequency in FREQUENCY_ENUM else "UNKNOWN",
            "explicit_times": [str(t) for t in times] if isinstance(times, list) else [],
            "with_food": bool(item.get("with_food")),
        })
    return medications


def extract_medications(raw_text: str) -> dict:
    """Blocking. Returns `{medications, model, elapsed_seconds, retried}`.

    Raises `RxExtractError` on anything that means the model did not
    successfully produce a parseable proposal list. One corrective retry is
    attempted on unparseable JSON, inside the shared 60 s budget.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RxExtractError("EMPTY_RAW_TEXT", "raw_text is empty -- nothing to extract")

    started = time.monotonic()
    messages = [{"role": "user", "content": PROMPT + raw_text}]

    def _remaining() -> float:
        return TOTAL_BUDGET_SECONDS - (time.monotonic() - started)

    content = _post_chat(messages, timeout=max(_remaining(), 1.0))
    retried = False
    try:
        medications = _coerce_medications(_extract_json_object(content))
    except (ValueError, json.JSONDecodeError) as first_error:
        remaining = _remaining()
        if remaining < MIN_RETRY_BUDGET_SECONDS:
            raise RxExtractError(
                "MODEL_OUTPUT_UNPARSEABLE",
                f"model output was not usable JSON and no retry budget remained: {first_error}",
            ) from first_error
        retried = True
        retry_messages = [
            *messages,
            {"role": "assistant", "content": content},
            {"role": "user", "content": _RETRY_INSTRUCTION},
        ]
        content = _post_chat(retry_messages, timeout=remaining)
        try:
            medications = _coerce_medications(_extract_json_object(content))
        except (ValueError, json.JSONDecodeError) as second_error:
            raise RxExtractError(
                "MODEL_OUTPUT_UNPARSEABLE",
                f"model output was not usable JSON after one corrective retry: {second_error}",
            ) from second_error

    return {
        "medications": medications,
        "model": RX_MODEL,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "retried": retried,
    }


def ollama_status() -> str:
    """`"ok"` when Ollama answers and the configured model is pulled;
    otherwise a short reason string. Non-fatal by construction -- /health
    reports it, and pill/Q&A are unaffected either way."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=2.0) as response:
            payload = json.loads(response.read())
    except Exception:  # noqa: BLE001 -- /health must never raise
        return "ollama_unreachable"
    names = {str(m.get("name", "")) for m in payload.get("models", []) if isinstance(m, dict)}
    if RX_MODEL not in names and f"{RX_MODEL}:latest" not in names:
        return "model_not_pulled"
    return "ok"


# --- HTTP surface -----------------------------------------------------------
#
# Shipped as an APIRouter rather than an `@app.post` in app.py so the whole
# endpoint stays importable/testable from the backend's venv without pulling
# in torch (via imb1) -- see dev/backend/tests/test_rx_extract_sidecar.py.

router = APIRouter()


class RxExtractRequest(BaseModel):
    raw_text: str


@router.post("/rx/extract")
async def rx_extract(body: RxExtractRequest) -> dict:
    try:
        return await run_in_threadpool(extract_medications, body.raw_text)
    except RxExtractError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
