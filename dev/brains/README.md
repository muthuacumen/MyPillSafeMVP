# PillSafe Brains Sidecar

A small FastAPI microservice that makes the frozen `IMB1_v0` (pill vision)
and `SB2` (deterministic matcher) packages callable over HTTP from the app
backend, without pulling torch/paddle into the app's own Python 3.11 venv.

This started as **Phase 1** of the PillSafe app x brains integration
(`documentation/integration/INTEGRATION_PLAN.md`); **Phase 4** added the BB3
Q&A endpoints (`/qa/chat`, `/qa/guard`) below. It does not touch the frozen
packages at `D:\Projects\PillSafe\{IMB1_v0,SB2,BB3}` in any way -- it only
imports them.

## Setup

Requires Python 3.12 (find one with `py -0p`; on this machine that's the
Windows Store Python at
`C:\Users\<you>\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe`).

```powershell
cd dev\brains
py -3.12 -m venv .venv
```

Install (heavy CUDA pins mirror `IMB1_Prototype\.venv`'s known-good freeze --
see `requirements.txt` for why; installs are several GB, budget real time):

```powershell
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install numpy==2.3.5 opencv-python==5.0.0.93 opencv-contrib-python==4.10.0.84 pillow==12.2.0 colour-science==0.4.7 fastapi uvicorn python-multipart httpx rapidfuzz pandas openpyxl "pytest>=7.0"
.\.venv\Scripts\pip.exe install torch==2.13.0+cu126 torchvision==0.28.0+cu126 --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\pip.exe install ultralytics==8.4.90
.\.venv\Scripts\pip.exe install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
.\.venv\Scripts\pip.exe install paddleocr==3.7.0
.\.venv\Scripts\pip.exe install scikit-image==0.26.0 scikit-learn==1.9.0
```

> **Note:** `scikit-image` and `scikit-learn` are real, undeclared
> dependencies of `imb1/colour.py` (`skimage.color.rgb2lab` for the hex->LAB
> centroid table; `sklearn`'s k-means for the CIELAB colour clustering
> described in `IMB1_v0/README.md`) that are missing from
> `IMB1_v0/requirements.txt`. Without them, `import imb1` fails at import
> time (`skimage`) or `analyze_pill()` fails at call time with
> `PILL_ANALYSIS_FAILED: No module named 'sklearn'`. Found while building
> this sidecar; pinned here to the versions in the known-good
> `IMB1_Prototype\.venv` reference (`0.26.0` / `1.9.0`).

(CPU-only machines: drop the `--index-url`/`-i` flags and let pip resolve
plain `torch`/`torchvision`/`paddlepaddle` -- much slower per `analyze_pill`
call, see `IMB1_v0/README.md` "GPU vs CPU".)

## Configuration

Env vars (all optional -- defaults resolve as siblings of this repo's parent
directory, e.g. `D:\Projects\PillSafe\{IMB1_v0,SB2,BB3}`, falling back to
those literal Windows paths if that resolution fails):

| Var | Default |
|---|---|
| `IMB1_ROOT` | `<repo-parent>\IMB1_v0` |
| `SB2_ROOT` | `<repo-parent>\SB2` |
| `BB3_ROOT` | `<repo-parent>\BB3` |
| `BRAINS_PORT` | `8100` |

BB3's runtime deps (`rank_bm25`, `sentence-transformers`, `ollama` -- the
Python client library, only needed for `mode="full"`) are also pinned in
`requirements.txt` (Phase 4). `ollama serve` + `qwen2.5:7b-instruct` pulled
are required at runtime ONLY for `POST /qa/chat` with `mode="full"` (the
offline fallback voice) -- `mode="context"` (the default, CB4's path) never
requires Ollama and never instantiates `BB3Engine`.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
```

First request is slow (FastSAM/S2/PaddleOCR model load + a fresh OCR
subprocess spawn per call) -- give callers timeouts of >=180s, per
`IMB1_v0/README.md`'s "two-process constraint" section. Do not run Ollama
alongside this service (GPU contention; unrelated to this phase anyway).

## Endpoints

- `GET /health` -- import status of imb1/sb2 (errors reported as strings,
  never a crash), reference row count, CUDA availability, `ocr_worker`
  (`"present"`/`"missing"` -- a file-exists check on `rx_ocr_sub.py`, never a
  paddle import or a probe subprocess, since this is polled every 30s),
  resolved package roots.
- `POST /ocr/prescription` (Task A1, deploy-readiness build) -- multipart
  `image` (required), a prescription LABEL photo. Spawns `rx_ocr_sub.py` --
  a second, independent, torch-free subprocess (mirrors `imb1.ocr_sub`'s
  pattern) -- via `sys.executable`, so this process still never imports
  paddle. Returns `{"raw_text": str, "line_count": int, "elapsed_seconds":
  float}`. 503 on any subprocess failure/timeout (with the subprocess's
  stderr tail in the message) -- never an empty-but-200 response, so the
  backend (`app/services/ocr_service.py`) can always tell "no text found"
  apart from "OCR did not run". Measured ~10-45s per call on this machine's
  GPU (subprocess spawn + model load + inference every time -- there is no
  persistent OCR worker, by design, matching `imb1.ocr_sub`'s own
  per-subprocess model load).
- `POST /pill/analyze` -- multipart `image` (required) + form `profile_dins`
  (optional JSON array of DIN strings, e.g. `["DIN4596","DIN13285"]`). Runs
  `imb1.analyze_pill` on a temp copy of the upload (cleaned up after), then
  `sb2.match_pill` if the pill was detected and `profile_dins` is non-empty.
  Returns `{"record": ..., "match": ...}` with every field either function
  returned, verbatim (including diagnostics and `ranked_candidates`).
- `GET /reference/search?q=<text>&limit=<n=10>` -- fuzzy name search
  (rapidfuzz `WRatio`, uppercase-normalized) over the SB2 reference table's
  `product` column. Returns `[{din, product, strength, score}]`, DINs in the
  same `"DIN####"` format `sb2.match_pill` expects.
- `GET /reference/candidates?dins=<comma-separated>` -- wraps
  `sb2.reference.get_candidates`, rows as JSON.

The reference table is loaded once at process startup (shared with SB2's own
`lru_cache`'d loader), not per request.

- `POST /qa/chat` -- body `{message, din?, confirmed_name?, mode?}`
  (`mode` defaults to `"context"`).
  - `mode="context"` (default, CB4's path): mirrors `BB3Engine.chat()`'s
    pre-generation control flow field-for-field via `qa.py` (imports the
    frozen `bb3.resolver`/`bb3.enumerate`/`bb3.retrieve`/`bb3.store`
    modules -- never edits them). Short-circuit statuses
    (confirm/pick_list/not_found/no_entity/enumeration/refused_dosing/
    empty-retrieval abstention) return byte-identical dicts to what
    `chat()` would return (minus `latency_s`), plus `"voice": "none"`.
    When generation would happen, returns `"status": "context_ready"`
    with the packed cited context (`packed_sources`, `offered_tags`,
    `schema`, `entity_names`, plus `resolution`/`sources`/`tier`/
    `disclaimer`) instead of calling an LLM -- the app's `cb4_service.py`
    hands this to Claude. Never requires Ollama, never instantiates
    `BB3Engine`.
  - `mode="full"` (offline fallback): a cached `BB3Engine()` singleton
    runs its own local-7B generation (`qwen2.5:7b-instruct` via Ollama)
    verbatim, plus `"voice": "local_7b"`. 503 `OLLAMA_UNAVAILABLE` if
    Ollama isn't running.
- `POST /qa/guard` -- body `{answer, sources_used, abstained, entity_names}`
  runs BB3's single-shot post-generation guards (`bb3.guards`) against an
  already-generated answer -- entity guard, ingredient-consistency,
  structured-abstention consistency. Returns `{entity_violation,
  ingredient_violation, structural_inconsistency}`. No retry logic here --
  the app backend (`cb4_service.answer_question`) owns the retry protocol
  (mirrors `bb3.guards.check_and_fix`).

`GET /health` also reports `bb3_ok` (imports resolved + store openable) and
`ollama_up`.

## Test

The sidecar's **own** suite (offline -- no live service, no Ollama, no GPU;
runs in-process through FastAPI's TestClient):

```powershell
cd dev\brains
.\.venv\Scripts\python.exe -m pytest tests -v
```

Covers the reference/search/profile/candidates HTTP contract, including the
`SEARCH_SCORE_CUTOFF` regression guard -- absent medications must return an
EMPTY list, because the app's `not_in_reference` guardrail flag fires only on
an empty list. Anything unavailable in the environment (no profile CSV, no
SB2 package) is skipped with a reason rather than failed. Pill analysis is
deliberately NOT here -- it needs real images and a Paddle subprocess, so it
stays in `smoke_test.py` below.

SB2's own suite, run from the SB2 package directory using this venv's python
(matches how SB2/README says to run it):

```powershell
cd D:\Projects\PillSafe\SB2
D:\Projects\PillSafe\PillSafe\dev\brains\.venv\Scripts\python.exe -m pytest tests -v
```

BB3's own suite, run from the BB3 package directory using this venv's python:

```powershell
cd D:\Projects\PillSafe\BB3
D:\Projects\PillSafe\PillSafe\dev\brains\.venv\Scripts\python.exe -m pytest tests -v
```

Sidecar smoke tests (run the service first, then in another shell):

```powershell
cd dev\brains
.\.venv\Scripts\python.exe smoke_test.py       # IMB1+SB2 (Phase 1)
.\.venv\Scripts\python.exe qa_smoke_test.py     # BB3 Q&A /qa/chat mode=context, all 7 statuses (Phase 4)
.\.venv\Scripts\python.exe parity_check.py      # BB3Engine.chat() vs qa.chat_context() diff (Phase 4; needs Ollama up)
```

## Known limitations / notes for the next phase

- No cloud API keys here by design (SB2/BB3 are local-only). CB4 (the only
  cloud call in the system) lives app-side in `dev/backend/app/services/
  cb4_service.py`.
- Multi-pill photos are out of scope (IMB1_v0 v0 scope: one pill per photo).
- The SB2 reference snapshot (`SB2/data/ca_appearance_harmonized_v2.xlsx`) is
  demo-grade -- see `SB2/README.md`.
- BB3's resolver has a measured quirk worth knowing about (frozen, not
  fixed here): the common word "daily" survives the distinctive-brand-token
  filter and resolves as if it were a brand, which can pull unrelated
  PM-sourced products into the DIN set for phrasings like "what is the
  maximum daily dose of X" -- e.g. it silently defeated the dosing-refusal
  gate for a no-PM-only product in one Phase 4 test case. Rephrasing without
  "daily" (e.g. "how much X can I take") avoids it. See BB3/CONTRACT.md's
  own "Known limitations" section for the class of issue this belongs to.
