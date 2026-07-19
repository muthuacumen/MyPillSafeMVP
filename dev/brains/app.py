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
"""
from __future__ import annotations

import json as json_mod
import math
import os
import tempfile
from typing import Any

import config  # noqa: F401  -- side effect: inserts IMB1_ROOT/SB2_ROOT/BB3_ROOT onto sys.path
import qa  # noqa: E402  -- BB3 Q&A context-mode + guard support (Phase 4)

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

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
        "reference_rows": reference_rows,
        "torch_cuda_available": torch_cuda_available,
        "roots": {
            "IMB1_ROOT": config.IMB1_ROOT,
            "SB2_ROOT": config.SB2_ROOT,
            "BB3_ROOT": config.BB3_ROOT,
        },
    }


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

@app.get("/reference/search")
def reference_search(q: str, limit: int = 10) -> list[dict]:
    if _REFERENCE_DF is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "REFERENCE_UNAVAILABLE", "message": _REFERENCE_LOAD_ERROR or "reference table not loaded"}},
        )
    if process is None or fuzz is None:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "RAPIDFUZZ_UNAVAILABLE", "message": "rapidfuzz not importable"}},
        )

    q_norm = (q or "").strip().upper()
    if not q_norm:
        return []

    # din -> uppercase product name, for fuzzy matching against bare user text.
    choices = _REFERENCE_DF["product"].fillna("").astype(str).str.upper().to_dict()
    matches = process.extract(q_norm, choices, scorer=fuzz.WRatio, limit=limit)

    results = []
    for _matched_string, score, din in matches:
        row = _REFERENCE_DF.loc[din]
        strength = row.get("strength")
        results.append({
            "din": row["din"],
            "product": row["product"],
            "strength": None if strength is None or (isinstance(strength, float) and math.isnan(strength)) else strength,
            "score": round(float(score), 2),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return _json_safe(results)


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
            qa.run_guards, body.answer, body.sources_used, body.abstained, body.entity_names
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
