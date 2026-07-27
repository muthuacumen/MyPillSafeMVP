# Part A Builder Prompt — deploy-readiness code work (MyPillSafe → mypillsafe.ca)

**Authored by:** PillSafe SA, 2026-07-27. **Executor:** Sonnet builder agent.
**Repo:** `D:\Projects\PillSafe\PillSafe` (app repo). **HEAD:** `85f39e6`.

This is **Part A** of the production deploy. Part B (Tailscale, GHCR, droplet, DNS,
TLS) is pure infra and is NOT your job — do not attempt it, do not install
Tailscale, do not touch the droplet, do not push anything anywhere.

---

## 0. Non-negotiables (violating any of these fails the build)

1. **The three frozen packages are READ-ONLY.** `D:\Projects\PillSafe\{IMB1_v0, SB2, BB3}`
   must not be modified. Read them for reference (you will mirror a pattern from
   `IMB1_v0\imb1\ocr_sub.py`) but never write there. Verify untouched at the end.
2. **Decision tokens are byte-identical.** `success` / `warning` / `danger` in
   `dev/frontend/tailwind.config.ts` and `PillResultPanel.tsx` must not change.
   You should not need to touch the frontend at all.
3. **Never fabricate medical data.** This build's central change is *removing* a
   path that invents a prescription. Do not add another one.
4. **No secrets committed.** `.env.production.example` carries placeholders only.
   Never copy a real `LLM_API_KEY`, password, or token into a tracked file.
5. **Commit nothing.** Leave the working tree dirty; Muthu commits.
6. **`torch` and `paddle` must never share one process** (Windows cuDNN
   WinError 127). `dev/brains/app.py` already imports torch transitively via
   `imb1`; its docstring says *"Do not import paddle here"* — that stays true.
   All PaddleOCR work happens in a **subprocess**.
7. **Report honestly.** If a bar fails, say so with the output. Do not soften.
   Every mandated smoke test in this project's history has caught at least one
   real bug — expect yours to, and report it rather than working around it.

---

## Task A1 — Sidecar gains a prescription-OCR endpoint

**Why:** OB5's PaddleOCR currently runs inside the app backend. On the deploy
target (a 4 GB droplet co-tenanted with a live site) that is a ~3 GB image, a
~1.5 GB RAM spike per scan, and a measured **~2m21s CPU** per label. Moving it to
the sidecar puts it on a GPU laptop and slims the droplet image.

### A1.1 — `dev/brains/rx_ocr_sub.py` (new)

A standalone, **paddle-only, torch-free** subprocess worker. Model it closely on
`D:\Projects\PillSafe\IMB1_v0\imb1\ocr_sub.py` (read it first):

- Copy its `modelscope.utils.torch_utils` stub **verbatim, before any paddleocr
  import**. That stub is why the existing worker stays torch-free; it was
  diagnosed 2026-07-09 and is load-bearing.
- Reuse its version-tolerant `make_ocr()` constructor idea (3.x pipeline kwargs
  first, 2.x legacy kwargs second, bare `PaddleOCR(lang="en")` last) and its
  `run_ocr()` result-shape handling (`rec_texts` under 3.x, nested tuples under 2.x).
- Do **not** import `config.py` — this script must stay independent of the
  torch-bearing sys.path injection.
- CLI: `--image <path> --out-json <path>`.
- Output JSON: `{"raw_text": "<lines joined by \n>", "lines": [...], "line_count": N}`.
- Exit non-zero with a message on stderr if OCR fails.

Note: the backend's old CPU engine passed `enable_mkldnn=False` to dodge a
paddlepaddle 3.3.1 **CPU-build** oneDNN crash. The sidecar venv runs
`paddlepaddle-gpu`, so do not blindly copy that flag — follow IMB1's constructor
instead. If the GPU path errors, report the actual error; don't guess.

### A1.2 — `dev/brains/app.py` (modify)

Add `POST /ocr/prescription`:

- Accepts `image: UploadFile = File(...)`.
- Writes bytes to a temp file (the module already imports `tempfile`), spawns
  `[sys.executable, str(RX_OCR_SUB), "--image", img, "--out-json", out]` with
  `subprocess.run(..., capture_output=True, text=True, timeout=300)`, wrapped in
  `run_in_threadpool` so it doesn't block the event loop.
- Returns `{"raw_text": str, "line_count": int, "elapsed_seconds": float}`.
- On subprocess failure/timeout → `HTTPException(503)` with a clear message
  including the subprocess stderr tail. Never return an empty-but-successful
  response for a failed run — the caller must be able to tell them apart.
- Always clean up both temp files (`finally`).
- Extend `/health` with `"ocr_worker": "present" | "missing"` (file-exists check
  only — do not import paddle or spawn a probe on every health call; health is
  hit by the pool checker every 30s).

---

## Task A2 — Backend calls the sidecar for OCR, and stops fabricating prescriptions

### A2.1 — `dev/backend/app/services/ocr_service.py` (rewrite)

Replace the local PaddleOCR engine with an HTTP client:

- `async def extract_text(image_bytes: bytes, filename: str, content_type: str) -> str`
- POSTs multipart to `{await resolve_brains_url()}/ocr/prescription` (see A3),
  `httpx.AsyncClient(timeout=300.0)` — OCR is genuinely slow; a short timeout
  here would manufacture failures.
- Keep the `OcrUnavailableError` class and raise it on **any** failure
  (connection error, timeout, non-200, malformed JSON, missing `raw_text`).
- Delete the paddle import, the engine singleton, and the threading lock.
- Docstring must state that the image is sent over the private tailnet to a
  team-run sidecar, and that failure raises rather than degrading.

### A2.2 — `dev/backend/app/api/v1/routes/prescriptions.py` (modify)

Current behaviour (`upload_prescription`): any OCR failure falls back to
`_DEMO_RAW_TEXT` = `"Metformin HCl 500mg — twice daily with meals..."`. **In a
medication-safety app, silently inventing a prescription from a failed scan is the
worst available failure mode**, and it directly contradicts the project's
abstain-over-guess principle. Now that OCR is a remote call, that path becomes
reachable in normal operation, so it must go.

New behaviour:

| Condition | Result |
|---|---|
| `OCR_PIPELINE_ENABLED=true` (default), OCR succeeds | parse real text (unchanged) |
| `OCR_PIPELINE_ENABLED=true`, OCR fails/unreachable | **HTTP 503**, `{"error": {"code": "OCR_UNAVAILABLE", "message": "..."}}` |
| `OCR_PIPELINE_ENABLED=false` | demo text — **explicit local-dev opt-out only** |

- Keep saving the uploaded image before OCR (upload persists regardless).
- Keep `_DEMO_RAW_TEXT` **only** for the flag-off branch, and comment it as a
  local-dev switch that fabricates text and must never be set false in production.
- Update `.env.example`'s `OCR_PIPELINE_ENABLED` comment accordingly.
- The 503 message must be user-safe and honest (e.g. "Prescription scanning is
  temporarily unavailable. Please try again shortly."). Do not leak the sidecar URL
  to end users in the user-facing string; log the URL server-side instead.

### A2.3 — Frontend check (read-only unless broken)

Confirm the Rx-upload UI surfaces a backend 503 as a visible error rather than a
silent hang or a fake success. If it already handles non-2xx generically, change
nothing and say so. If it would show a fabricated success, fix minimally and
report exactly what you changed.

---

## Task A3 — Sidecar pool: health-checked selection + admin override

**Why:** five team members may each run a sidecar on their own laptop; a closed
laptop must not take the demo down.

### A3.1 — `dev/backend/app/core/config.py`

Add `BRAINS_SERVICE_URLS: str = ""` (comma-separated). Keep the existing
`BRAINS_SERVICE_URL` exactly as-is for back-compat.

### A3.2 — `dev/backend/app/services/brains_registry.py` (new)

```
async def resolve_brains_url() -> str
async def pool_status() -> list[dict]     # [{url, healthy, latency_ms, checked_at, pinned}]
def set_pin(url: str | None) -> None
def get_pin() -> str | None
```

Rules — read these carefully, the back-compat one matters most:

1. **If `BRAINS_SERVICE_URLS` is empty → `resolve_brains_url()` returns
   `settings.BRAINS_SERVICE_URL` immediately, with NO health check.** This keeps
   every existing test and every single-sidecar dev setup byte-identical in
   behaviour and adds zero latency. Do not skip this.
2. With a pool configured: return the pinned URL if pinned **and** healthy; else
   the first healthy URL in list order; else the **first URL in the list** (so
   downstream 503 messages still name a concrete host and existing error paths
   behave unchanged).
3. Health = `GET {url}/health`, 2s timeout, 200 = healthy. Cache each URL's result
   for 30s in module state (a plain dict — no DB, no extra dependency).
4. Never raise. A registry failure must degrade to rule 2's fallback.

### A3.3 — Convert the five call sites

Replace every `settings.BRAINS_SERVICE_URL` read with `await resolve_brains_url()`:

- `app/api/v1/routes/pill.py:124,129,136`
- `app/api/v1/routes/qa.py:48,86`
- `app/services/brains_client.py:54,107`
- `app/services/cb4_service.py:178`

Resolve **once per request** into a local variable and reuse it for both the call
and its error message — do not call the resolver twice in one handler (the URL
could differ between calls and produce a misleading error). `qa.py`'s
`_brains_unreachable_error()` is a module-level helper that reads the setting;
give it a `url` parameter. Verify each call site is in an async context first.

### A3.4 — Admin endpoints (`app/api/v1/routes/admin.py`)

- `GET /admin/brains` → `pool_status()`.
- `POST /admin/brains/pin` body `{"url": str | null}` → pin/unpin; **422** if the
  URL is not in the configured pool (never accept an arbitrary URL — that would be
  an SSRF hole in an admin-authenticated endpoint).
- Both under the existing admin auth dependency used by the neighbouring routes.

---

## Task A4 — Slim the backend image

- `dev/backend/requirements-optional.txt`: remove `paddleocr` and `paddlepaddle`.
  **Before removing `pillow` / `numpy`, grep `dev/backend/app/` for `PIL` and
  `numpy` imports** — keep whichever are still genuinely used, and say in your
  report what you found.
- `dev/backend/Dockerfile`: remove what existed only for paddle — the
  `LD_PRELOAD=/lib/x86_64-linux-gnu/libz.so.1` line, the `cython<3.0` pin, and the
  paddle-only apt packages, **with one caution**: `faster-whisper`/`ctranslate2`
  uses OpenMP and needs `libgomp1`. Keep `libgomp1`. Decide `libgl1` /
  `libglib2.0-0` by checking what remains — and prove your decision by building the
  image and running the suite inside it, not by reasoning alone.
- Update the header comments in both files so they describe the new reality
  (OCR is remote; these deps are gone and why).

---

## Task A5 — Production deployment artifacts

### A5.1 — `docker/docker-compose.prod.yml` (new, overlay)

Used as `docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ...`.

- **`ports` must be overridden so NOTHING binds `0.0.0.0`.** The base file publishes
  host `:80` (gateway), `:5173`, `:8000`, `:5433`, `:6379`. On the droplet, host `:80`
  is already serving two live sites — publishing it would break them.
  In the overlay: gateway nginx → `"127.0.0.1:8080:80"`; backend, frontend, postgres,
  redis publish **nothing** (`ports: []`).
- `image: ghcr.io/muthuacumen/mypillsafe-backend:${IMAGE_TAG:-latest}` and
  `...-frontend:${IMAGE_TAG:-latest}`; `pull_policy: always`.
- `mem_limit` on every service (cgroup cap — the droplet guardrail that stops a
  PillSafe balloon from OOM-killing the neighbouring live site):
  backend `800m`, postgres `384m`, frontend `96m`, nginx `64m`, redis `64m`.
- `restart: always`.
- **Drop `extra_hosts: host.docker.internal`** and add this comment: in production
  the sidecar is reached at a **raw Tailscale IP (100.x.y.z)**, never a MagicDNS
  hostname — containers use Docker's resolver and will not resolve tailnet names.
- The frontend service's `spa.conf` bind mount must still work from the compose
  file's directory.

### A5.2 — `docker/nginx/mypillsafe.ca.conf` (new)

The **host** nginx site for the droplet (not a container config):

- `server_name mypillsafe.ca www.mypillsafe.ca;`
- `proxy_pass http://127.0.0.1:8080;` with `Host`, `X-Real-IP`,
  `X-Forwarded-For`, `X-Forwarded-Proto`.
- `client_max_body_size 20M;` — phone photos are 3–5 MB; the nginx default of 1M
  would reject them. (The container gateway already sets 20M in `nginx.conf:23` —
  match it.)
- `proxy_read_timeout 300s;` — must clear the OCR round-trip.
- Plain HTTP only, with a comment that certbot rewrites this file for TLS in Part B.

### A5.3 — `.env.production.example` (new)

Placeholders only. Include `APP_ENV=production`, `OPENAPI_ENABLED=false`,
`FRONTEND_ORIGIN=https://mypillsafe.ca`, a strong-`SECRET_KEY` placeholder,
`POSTGRES_PASSWORD` placeholder, `LLM_API_KEY=` (blank), `OCR_PIPELINE_ENABLED=true`,
`BRAINS_SERVICE_URLS=http://100.x.y.z:8100,http://100.a.b.c:8100`, `IMAGE_TAG=latest`.
Comment each block. State plainly that `OCR_PIPELINE_ENABLED=false` fabricates
prescription text and must never be used in production.

### A5.4 — README / CI badge

Repoint `muthuacumen/mypillsafe` → `muthuacumen/MyPillSafeMVP` wherever it appears
(CI badge, clone URLs). **README stays number-free** — that rule is binding
(no measured metrics in public copy).

---

## Verification bar (pre-registered — run ALL of it, report each line)

| # | Check | Pass condition |
|---|---|---|
| 1 | `pytest` in `dev/backend` | ≥ 109 passed, 0 failed (expect a higher count — you're adding tests) |
| 2 | Frontend `npm run type-check` + `npm run build` | clean |
| 3 | Sidecar starts with the new endpoint | `/health` 200, `ocr_worker: "present"` |
| 4 | **Real Rx label → real text** | POST an actual photo from `dev/backend/uploads/prescriptions/<id>/` to `/ocr/prescription`; non-empty `raw_text` that plausibly matches the label. **Report `elapsed_seconds`** — this number is currently unmeasured on GPU and Part B's timeout budget depends on it |
| 5 | E2E through the app | Real Rx upload via the backend (sidecar up) → real parsed medications, not Metformin demo text |
| 6 | **Honest degradation** | Stop the sidecar → Rx upload returns **503 `OCR_UNAVAILABLE`**, and NOT `_DEMO_RAW_TEXT` |
| 7 | Pool failover | `BRAINS_SERVICE_URLS=<dead>,<live>` → resolves to live; `GET /admin/brains` shows both with correct health |
| 8 | Pool back-compat | `BRAINS_SERVICE_URLS` unset → behaviour identical to before, no health-check latency |
| 9 | Pin safety | `POST /admin/brains/pin` with a URL outside the pool → 422 |
| 10 | Slim image builds | `docker build dev/backend` succeeds; suite runs inside it; report the image size before vs after |
| 11 | **No public bind** | `docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config` renders, and grepping its output proves no `0.0.0.0` published port and no host `:80` |
| 12 | Frozen packages untouched | `IMB1_v0`, `SB2`, `BB3` unmodified (compare mtimes/hashes) |
| 13 | No secrets staged | `git status` + grep the new files for real keys/passwords |

If any bar fails and you cannot fix it within scope, **stop and report** with the
exact output. Do not mark a bar green that you did not actually run.

---

## Report format

1. What you changed, per file, one line each.
2. Every verification bar with its actual measured result (numbers, not adjectives)
   — especially #4's `elapsed_seconds` and #10's image sizes.
3. **Bugs found** (there is usually at least one — this project's mandated smoke
   tests have caught a real bug in every build so far).
4. Deviations from this spec and why.
5. Anything you consciously left for Part B.
