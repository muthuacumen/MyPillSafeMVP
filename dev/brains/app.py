"""PillSafe brains sidecar — FastAPI microservice that makes the frozen
IMB1_v0 (pill vision) and SB2 (deterministic matcher) packages callable over
HTTP from the main app backend.

Run (from this directory, using the sidecar venv):

    ./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100

See README.md for full setup instructions.

Two-process constraint (do not "fix" this): torch and paddle cannot share one
Windows process (cuDNN WinError 127). `imb1.analyze_pill()` already spawns its
own OCR subprocess internally via `sys.executable -m imb1.ocr_sub` -- since
this service runs under the sidecar venv's python, that subprocess correctly
reuses the same venv (which has paddleocr/paddlepaddle-gpu installed) without
this process ever importing paddle itself. Do not import paddle here.

`POST /ocr/prescription` (Task A1, app x brains deploy-readiness build) is
the same pattern applied to prescription-LABEL OCR (as opposed to pill-
imprint OCR): it spawns `rx_ocr_sub.py` -- a second, independent, torch-free
subprocess -- via `sys.executable`, so this process still never imports
paddle even though the backend now sends prescription photos here instead of
running PaddleOCR in-process itself (see backend/app/services/ocr_service.py).
"""
from __future__ import annotations

import json as json_mod
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import config  # noqa: F401  -- side effect: inserts IMB1_ROOT/SB2_ROOT/BB3_ROOT onto sys.path
import qa  # noqa: E402  -- BB3 Q&A context-mode + guard support (Phase 4)
import rx_extract  # noqa: E402  -- FixbyOPUS3 Task A1: POST /rx/extract (local qwen proposer)

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

# Prescription-label OCR (Task A1). A standalone, paddle-only, torch-free
# subprocess -- see its module docstring for why it must never be imported
# directly into this (torch-holding, via imb1) process.
RX_OCR_SUB = Path(__file__).resolve().parent / "rx_ocr_sub.py"

# --- Import the frozen packages defensively -------------------------------
# Per spec: import checks must never crash the service. If either package (or
# a heavy dependency it needs) fails to import, /health must still respond
# and report the error as a string rather than 500ing or refusing to boot.

_imb1_import_error: str | None = None
_sb2_import_error: str | None = None

try:
    import imb1  # noqa: E402
except Exception as exc:  # pragma: no cover - defensive, exercised by /health
    imb1 = None  # type: ignore[assignment]
    _imb1_import_error = repr(exc)

try:
    from sb2 import match_pill as _sb2_match_pill  # noqa: E402
    from sb2 import reference as sb2_reference  # noqa: E402
except Exception as exc:  # pragma: no cover - defensive, exercised by /health
    _sb2_match_pill = None  # type: ignore[assignment]
    sb2_reference = None  # type: ignore[assignment]
    _sb2_import_error = repr(exc)

try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover - rapidfuzz is a hard sidecar dependency
    fuzz = None  # type: ignore[assignment]
    process = None  # type: ignore[assignment]


app = FastAPI(title="PillSafe Brains Sidecar", version="0.1.0")

# FixbyOPUS3 Task A1 -- `POST /rx/extract`. Lives in its own module so the
# endpoint is importable from the backend's venv (no torch/paddle) for tests.
app.include_router(rx_extract.router)


# --- Reference table: loaded ONCE at process startup, not per request ------

_REFERENCE_DF: pd.DataFrame | None = None
_REFERENCE_LOAD_ERROR: str | None = None


def _load_reference_once() -> None:
    global _REFERENCE_DF, _REFERENCE_LOAD_ERROR
    if sb2_reference is None:
        _REFERENCE_LOAD_ERROR = _sb2_import_error or "sb2 package not importable"
        return
    try:
        # Reuse SB2's own loading code (lru_cache'd `_load`) so we get the
        # exact same DIN-indexed, dedup-validated frame that
        # `sb2.reference.get_candidates` uses internally -- one load, shared
        # cache, no drift between what /reference/search sees and what
        # /pill/analyze's matching sees.
        _REFERENCE_DF = sb2_reference._load(str(sb2_reference._DEFAULT_XLSX))
    except Exception as exc:
        _REFERENCE_LOAD_ERROR = repr(exc)


_load_reference_once()


# --- PROFILE reference tier (FixbyOPUS3 Task B2) ---------------------------
#
# Two tiers, two questions, deliberately not the same table:
#
#   APPEARANCE tier (_REFERENCE_DF, 7,055 DINs, SB2's harmonized workbook)
#     answers "can a photo of this pill be verified?" -- it is the only tier
#     `/pill/analyze` and `/reference/candidates` ever touch, and NOTHING
#     about it changes here.
#
#   PROFILE tier (_PROFILE_DF, 11,609 DINs, profile_reference_v1.csv)
#     answers "is this a real Canadian medication, and what is its DIN?" --
#     the question prescription linking actually asks. Measured: 4,554
#     marketed human medicines (39%) are not pill-shaped -- insulin pens,
#     inhalers, creams, drops, patches -- and were previously un-linkable.
#
# `/reference/search` moves to the profile tier and returns `pill_verifiable`
# so the app can say which linked medications a photo can and cannot check,
# instead of quietly omitting the ones it cannot.

_PROFILE_CSV = Path(__file__).resolve().parent / "data" / "profile_reference_v1.csv"
_PROFILE_DF: pd.DataFrame | None = None
_PROFILE_LOAD_ERROR: str | None = None
_STRENGTH_BY_DIN: dict[str, Any] = {}


def _load_profile_reference_once() -> None:
    global _PROFILE_DF, _PROFILE_LOAD_ERROR, _STRENGTH_BY_DIN
    # Strengths live only in the appearance tier (the DPD snapshot the
    # profile tier is generated from carries no strength column), so a
    # profile-tier hit that IS pill-verifiable can still show one.
    if _REFERENCE_DF is not None and "strength" in _REFERENCE_DF.columns:
        _STRENGTH_BY_DIN = _REFERENCE_DF["strength"].to_dict()
    if not _PROFILE_CSV.exists():
        _PROFILE_LOAD_ERROR = f"profile reference CSV not found at {_PROFILE_CSV}"
        return
    try:
        frame = pd.read_csv(_PROFILE_CSV, dtype={"din": str})
        _PROFILE_DF = frame.set_index("din", drop=False)
    except Exception as exc:
        _PROFILE_LOAD_ERROR = repr(exc)


_load_profile_reference_once()


# --- JSON-safety helper -----------------------------------------------------
# imb1/sb2 return plain dicts, but individual scalar values inside them (or
# inside pandas-derived reference rows) can be numpy scalars (np.float32,
# np.int64, np.bool_) or NaN, none of which the stdlib json encoder handles
# cleanly. Recursively normalize to native Python types before returning.

def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _json_safe(obj.tolist())
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if obj is pd.NaT:
        return None
    return obj


# --- /health -----------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    if _REFERENCE_DF is not None:
        reference_rows: Any = int(len(_REFERENCE_DF))
    else:
        reference_rows = _REFERENCE_LOAD_ERROR or "unavailable"

    try:
        import torch
        torch_cuda_available: Any = bool(torch.cuda.is_available())
    except Exception as exc:
        torch_cuda_available = f"error: {exc!r}"

    return {
        "status": "ok",
        "imb1_ok": True if _imb1_import_error is None else _imb1_import_error,
        "sb2_ok": True if _sb2_import_error is None else _sb2_import_error,
        "bb3_ok": qa.bb3_ok(),
        "ollama_up": qa.ollama_up(),
        # Appearance tier (SB2's harmonized workbook) -- what /pill/analyze
        # and /reference/candidates use. Unchanged by Task B.
        "reference_rows": reference_rows,
        # Profile tier (FixbyOPUS3 Task B2) -- what /reference/search uses.
        "profile_reference_rows": (
            int(len(_PROFILE_DF)) if _PROFILE_DF is not None
            else (_PROFILE_LOAD_ERROR or "unavailable")
        ),
        "torch_cuda_available": torch_cuda_available,
        # File-exists check ONLY -- deliberately never imports paddle or spawns
        # a probe subprocess here. /health is polled by the pool checker every
        # 30s (see backend/app/services/brains_registry.py); a slow/heavy
        # check on that path would make health-checking itself a liability.
        "ocr_worker": "present" if RX_OCR_SUB.exists() else "missing",
        # FixbyOPUS3 Task A1: NON-FATAL. A down Ollama means Rx parsing
        # degrades to the backend's regex proposer; pill analysis and Q&A
        # context mode are unaffected, so this never flips `status`.
        "rx_extract": rx_extract.ollama_status(),
        "roots": {
            "IMB1_ROOT": config.IMB1_ROOT,
            "SB2_ROOT": config.SB2_ROOT,
            "BB3_ROOT": config.BB3_ROOT,
        },
    }


# --- /ocr/prescription -------------------------------------------------------

@app.post("/ocr/prescription")
async def ocr_prescription(image: UploadFile = File(...)) -> dict:
    """Prescription-label OCR (Task A1), proxied by the backend's
    `ocr_service.extract_text` (Task A2.1). Spawns `rx_ocr_sub.py` as a
    torch-free subprocess (see that module's docstring) via `sys.executable`
    -- this process itself never imports paddle.

    Never returns an empty-but-successful response for a failed run: any
    subprocess failure/timeout/malformed output raises HTTP 503 with the
    subprocess's stderr tail attached, so the caller can tell "OCR found no
    text" apart from "OCR did not run".
    """
    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    image_bytes = await image.read()

    img_tmp_path: str | None = None
    out_tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as img_tmp:
            img_tmp.write(image_bytes)
            img_tmp_path = img_tmp.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as out_tmp:
            out_tmp_path = out_tmp.name

        start = time.monotonic()
        try:
            proc = await run_in_threadpool(
                subprocess.run,
                [sys.executable, str(RX_OCR_SUB), "--image", img_tmp_path, "--out-json", out_tmp_path],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OCR_TIMEOUT",
                        "message": "Prescription OCR timed out after 300s.",
                    }
                },
            ) from exc
        elapsed_seconds = time.monotonic() - start

        if proc.returncode != 0:
            stderr_tail = "\n".join((proc.stderr or "").strip().splitlines()[-20:])
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OCR_SUBPROCESS_FAILED",
                        "message": f"rx_ocr_sub exited {proc.returncode}: {stderr_tail or '(no stderr)'}",
                    }
                },
            )

        try:
            with open(out_tmp_path, encoding="utf-8") as fh:
                result = json_mod.load(fh)
        except (OSError, json_mod.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OCR_OUTPUT_UNREADABLE",
                        "message": f"rx_ocr_sub produced no readable output JSON: {exc!r}",
                    }
                },
            ) from exc

        if "raw_text" not in result:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OCR_OUTPUT_MALFORMED",
                        "message": "rx_ocr_sub output JSON is missing 'raw_text'.",
                    }
                },
            )

        return {
            "raw_text": result["raw_text"],
            "line_count": result.get("line_count", len(result.get("lines", []))),
            "elapsed_seconds": round(elapsed_seconds, 3),
        }
    finally:
        for p in (img_tmp_path, out_tmp_path):
            if p and os.path.exists(p):
                os.remove(p)


# --- /pill/analyze -----------------------------------------------------------

@app.post("/pill/analyze")
async def pill_analyze(
    image: UploadFile = File(...),
    profile_dins: str | None = Form(None),
) -> dict:
    if imb1 is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "IMB1_UNAVAILABLE", "message": _imb1_import_error or "imb1 package not importable"}},
        )

    dins: list[str] = []
    if profile_dins:
        try:
            parsed = json_mod.loads(profile_dins)
        except json_mod.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "INVALID_PROFILE_DINS", "message": f"profile_dins must be a JSON array of DIN strings: {exc}"}},
            ) from exc
        if isinstance(parsed, list):
            dins = [str(d) for d in parsed]

    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    image_bytes = await image.read()

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            record = await run_in_threadpool(imb1.analyze_pill, tmp_path)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "PILL_ANALYSIS_FAILED", "message": str(exc)}},
            ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not record.get("detected"):
        # Per IMB1 CONTRACT.md: never pass an undetected record to SB2.
        return _json_safe({"record": record, "match": None})

    if dins:
        if _sb2_match_pill is None:
            raise HTTPException(
                status_code=503,
                detail={"error": {"code": "SB2_UNAVAILABLE", "message": _sb2_import_error or "sb2 package not importable"}},
            )
        match = await run_in_threadpool(_sb2_match_pill, record, dins)
        return _json_safe({"record": record, "match": match})

    return _json_safe({"record": record, "match": None, "note": "no profile DINs supplied — matching skipped"})


# --- /reference/search ---------------------------------------------------

def _clean_strength(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


#: Minimum `token_set_ratio` a product name must reach to be offered at all.
#: Below this the search returns NOTHING, which is what makes the app's
#: `not_in_reference` guardrail flag fire and warn the user -- that flag only
#: triggers on an EMPTY list, so before this cutoff existed it effectively
#: never fired.
#:
#: Chosen 2026-07-29 by sweeping 4 scorers x 9 cutoffs over 62 positives
#: (17 real label names + 45 sampled brands) and 21 negatives. Measured at
#: token_set_ratio/75: positives hit@5 60/62 -- IDENTICAL to the shipping
#: WRatio/no-cutoff baseline -- while negatives correctly returning empty go
#: from **0/21 to 19/21**. The previous scorer+no-cutoff combination returned
#: its top-N however bad they were: the nonsense query "ZZZQQQ 25 MG TAB"
#: came back with the same confident 85.5-scoring candidates as a real
#: digoxin query.
#:
#: The 2 negatives that still survive are genuine LASA pairs that no
#: threshold separates (ZOLTIRAX~ZOVIRAX 80.0, TYLENOL PM EXTRA~TYLENOL
#: EXTRA STRENGTH 89.7); raising the cutoff to catch them costs real
#: medications, so they stay a matter for the never-auto-pick rule rather
#: than for this number.
#:
#: The one real-label positive this loses is the OCR-noise string
#: "AT0RVASTATIN" (73.3). That is an acceptable, deliberate trade: a lost
#: positive returns EMPTY, which fires `not_in_reference` and tells the user
#: honestly that we could not find it (they can still search by hand), while
#: a surviving false suggestion is silent and can be linked -- poisoning SB2
#: with a wrong appearance row and BB3 with a wrong monograph. Honest and
#: recoverable beats silent and harmful. In the normal path the qwen proposer
#: repairs that OCR noise before the search ever sees it (measured); it only
#: reaches here on the regex fallback, i.e. already-degraded mode, where an
#: honest "not found" is the right answer anyway.
SEARCH_SCORE_CUTOFF = 75.0


@app.get("/reference/search")
def reference_search(q: str, limit: int = 10) -> list[dict]:
    """Fuzzy medication-name search over the PROFILE tier (11,609 marketed
    human DINs). `pill_verifiable` says whether that DIN is also in the
    appearance tier, i.e. whether a photo of it can be checked at all.

    Scored with `token_set_ratio` against `SEARCH_SCORE_CUTOFF`, so a
    medication that is genuinely absent comes back as an EMPTY list rather
    than as confident nonsense -- see that constant's comment.

    Falls back to the appearance tier if the profile CSV is missing, so a
    deployment that has not shipped `data/profile_reference_v1.csv` degrades
    to the pre-Task-B behaviour instead of 503ing prescription linking.
    """
    if process is None or fuzz is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "RAPIDFUZZ_UNAVAILABLE", "message": "rapidfuzz not importable"}},
        )

    using_profile_tier = _PROFILE_DF is not None
    frame = _PROFILE_DF if using_profile_tier else _REFERENCE_DF
    if frame is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "REFERENCE_UNAVAILABLE",
                    "message": _PROFILE_LOAD_ERROR or _REFERENCE_LOAD_ERROR or "reference table not loaded",
                }
            },
        )

    q_norm = (q or "").strip().upper()
    if not q_norm:
        return []

    name_column = "brand" if using_profile_tier else "product"
    # din -> uppercase product name, for fuzzy matching against bare user text.
    choices = frame[name_column].fillna("").astype(str).str.upper().to_dict()
    matches = process.extract(
        q_norm, choices,
        scorer=fuzz.token_set_ratio, limit=limit, score_cutoff=SEARCH_SCORE_CUTOFF,
    )

    results = []
    for _matched_string, score, din in matches:
        row = frame.loc[din]
        if using_profile_tier:
            pill_verifiable = bool(row["pill_verifiable"])
            strength = _STRENGTH_BY_DIN.get(din) if pill_verifiable else None
        else:
            pill_verifiable = True  # appearance tier == verifiable by definition
            strength = row.get("strength")
        results.append({
            "din": row["din"],
            "product": row[name_column],
            "strength": _clean_strength(strength),
            "score": round(float(score), 2),
            "pill_verifiable": pill_verifiable,
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return _json_safe(results)


# --- /reference/profile ----------------------------------------------------

@app.get("/reference/profile")
def reference_profile(dins: str = "") -> list[dict]:
    """PROFILE-tier lookup by DIN (FixbyOPUS3 Task B2/B3).

    Deliberately a SEPARATE endpoint from `/reference/candidates`, which
    serves the appearance tier and whose response shape SB2 + the pill-scan
    path depend on. This one answers a different question -- "is this DIN a
    marketed human medicine, and can a photo of it be checked?" -- and a
    DIN that is absent here is absent from the answer, so the caller can
    tell "not in the tier" apart from "the service is down" (an empty list
    vs. no response at all).
    """
    if _PROFILE_DF is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "PROFILE_REFERENCE_UNAVAILABLE",
                              "message": _PROFILE_LOAD_ERROR or "profile reference not loaded"}},
        )
    wanted = [d.strip() for d in dins.split(",") if d.strip()]
    if not wanted:
        return []
    found = _PROFILE_DF.reindex(wanted).dropna(subset=["din"])
    rows = found[["din", "brand", "company", "ingredients", "forms", "routes",
                  "schedules", "pill_verifiable"]].to_dict("records")
    for row in rows:
        row["pill_verifiable"] = bool(row["pill_verifiable"])
    return _json_safe(rows)


# --- /reference/candidates -------------------------------------------------

@app.get("/reference/candidates")
def reference_candidates(dins: str = "") -> list[dict]:
    if sb2_reference is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "SB2_UNAVAILABLE", "message": _sb2_import_error or "sb2 package not importable"}},
        )
    din_list = [d.strip() for d in dins.split(",") if d.strip()]
    rows = sb2_reference.get_candidates(din_list)
    return _json_safe(rows)


# --- /qa/chat + /qa/guard (BB3 Q&A, Phase 4) --------------------------------

class QAChatRequest(BaseModel):
    message: str
    din: str | None = None
    confirmed_name: str | None = None
    mode: str = "context"  # "context" (CB4 path, default) | "full" (offline fallback)


class QAGuardRequest(BaseModel):
    answer: str
    sources_used: list[str] = []
    abstained: bool = False
    entity_names: list[str] = []
    question: str | None = None  # WP2.5: enables the claim-source polarity guard
    packed_context: str | None = None  # WP2.5: the source sections the answer was generated against


@app.post("/qa/chat")
async def qa_chat(body: QAChatRequest) -> dict:
    if body.mode not in ("context", "full"):
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_MODE", "message": "mode must be 'context' or 'full'"}},
        )

    if body.mode == "full":
        # Offline fallback -- BB3Engine's own local-7B generation. Requires
        # Ollama; never instantiated for mode="context" (see qa.py module docstring).
        if not qa.ollama_up():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "OLLAMA_UNAVAILABLE",
                        "message": "Ollama is not running -- start it with `ollama serve` "
                        "(the offline fallback voice requires the local qwen2.5:7b-instruct model).",
                    }
                },
            )
        try:
            engine = await run_in_threadpool(qa.get_full_engine)
            result = await run_in_threadpool(engine.chat, body.message, body.din, body.confirmed_name)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": {"code": "BB3_ENGINE_ERROR", "message": str(exc)}},
            ) from exc
        return _json_safe({**result, "voice": "local_7b"})

    # mode == "context" -- never requires Ollama, never instantiates BB3Engine.
    if qa.bb3_import_error():
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "BB3_UNAVAILABLE", "message": qa.bb3_import_error()}},
        )
    try:
        result = await run_in_threadpool(qa.chat_context, body.message, body.din, body.confirmed_name)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "QA_CONTEXT_ERROR", "message": str(exc)}},
        ) from exc

    if result["status"] != "context_ready":
        result = {**result, "voice": "none"}
    return _json_safe(result)


@app.post("/qa/guard")
async def qa_guard(body: QAGuardRequest) -> dict:
    if qa.bb3_import_error():
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "BB3_UNAVAILABLE", "message": qa.bb3_import_error()}},
        )
    try:
        result = await run_in_threadpool(
            qa.run_guards, body.answer, body.sources_used, body.abstained, body.entity_names,
            body.question, body.packed_context,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "QA_GUARD_ERROR", "message": str(exc)}},
        ) from exc
    return _json_safe(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=config.BRAINS_PORT)
