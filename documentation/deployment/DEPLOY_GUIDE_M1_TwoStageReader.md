# MyPillSafe -- M1 Deploy Guide: the two-stage pill reader

**Target:** ship the M1 two-stage imprint reader (A3 presence gate -> A4c constrained
read) into the LIVE site at `https://mypillsafe.ca`, and run the capstone demo there.

**Scope:** this is a **sidecar-only** deploy. The droplet is not touched. See section 3
for the verified reason.

**Audience:** a Sonnet agent driving Muthu through this step by step, one step at a
time. **Written 2026-08-14 by PillSafe SA.** Companion to `DEPLOY_GUIDE.md` (the
infrastructure guide) -- that document remains the authority on anything droplet-side.

---

## How to use this guide (instructions for the assisting agent)

- Work **one step at a time**. After each CHECKPOINT, show Muthu the actual command
  output and get his go-ahead before moving on. Do not batch steps.
- Commands are labelled **[LAPTOP]** (Windows PowerShell) or **[DROPLET]** (bash over
  SSH). They are different shells on different machines.
- The site is **LIVE and public**. Every step here happens against production. There is
  no localhost rehearsal any more -- the localhost recording demo was dropped
  2026-08-14. Treat every "start" and "restart" as a user-visible outage window.
- Anything in `<angle brackets>` is a value Muthu supplies or that an earlier step
  produced. Never invent one.
- `TODO(builder)` marks a place where the concurrent M1 build's own report must supply
  the answer before this guide can be executed. **Do not guess past a TODO(builder).**
- If a checkpoint fails, stop and diagnose. Triage table at the end (section 6).

---

## 0. Facts and prerequisites

| Thing | Value |
|---|---|
| What changes | `dev/brains/` on the laptop only -- config, wiring, NB08 reader sources |
| What does NOT change | droplet images, compose files, nginx, DNS, TLS, Postgres schema |
| Sidecar | host-run on the GPU laptop, port `8100`, bound to the tailnet IP |
| Sidecar launcher | Task Scheduler task **`MyPillSafe Sidecar`** (TaskPath `\`) -> `D:\Projects\PillSafe\ops\start_sidecar.cmd` |
| Sidecar log | `D:\Projects\PillSafe\logs\sidecar.log` |
| Sidecar venv | `D:\Projects\PillSafe\PillSafe\dev\brains\.venv` (Python 3.12.10) |
| GPU | RTX 4060 Laptop, 8.6 GB VRAM |
| Ollama keep-alive | Task **`\PillSafe\OllamaHealthCheck`**, every 5 min + HKCU `Run` key at logon |
| Droplet | `134.122.34.26`; reaches the sidecar over Tailscale via `BRAINS_SERVICE_URLS` in `/opt/mypillsafe/repo/.env` |

**The deploy mechanism is the sidecar restart.** `dev/brains/`, `IMB1_v0/`, `SB2/`,
`BB3/` and `IMB1_Prototype/NB08_Notebook/src/` live on the laptop, in no image and no
compose file. Restarting the sidecar is the ONLY way a change to any of them reaches
production. Nothing is built or pushed for an M1 deploy.

### The two config knobs this whole guide turns on

From `dev/brains/config.py` (already merged):

| Variable | Default | Meaning |
|---|---|---|
| `PILLSAFE_READER` | `off` | `off` = legacy `imb1.analyze_pill`, byte-identical to the pre-M1 sidecar. `two_stage` = route through `production_wiring.analyze()` |
| `PILLSAFE_STAGE1` | `single` | `single` = presence gate runs on the same in-process NF4 4.4B weights as Stage 2. `ollama` = the 8.8B `qwen3-vl:latest` over Ollama HTTP |
| `PILLSAFE_SCORER_DEVICE` | `cuda` | `cpu` is ~47 s per forward pass with ~15 candidates per crop -- wiring smoke tests only, never a request |

**`PILLSAFE_READER` defaults to `off`.** A sidecar restart that sets nothing is
therefore a **safe no-op deploy** that ships the code without arming it. That is the
intended shape: arming the reader is a decision Muthu makes by setting a variable.

---

## 1. Pre-flight (do this BEFORE stopping anything)

Every check here is read-only and runs while the site is still serving.

### 1.1 -- The 4-bit scorer's dependencies (RESOLVED 2026-08-14)

```powershell
# [LAPTOP]
D:\Projects\PillSafe\PillSafe\dev\brains\.venv\Scripts\python.exe -c "import importlib.util as u; [print(k, 'PRESENT' if u.find_spec(k) else 'MISSING') for k in ['bitsandbytes','accelerate','transformers','torch']]"
```

**RESOLVED 2026-08-14.** The blocker recorded earlier in this section (`bitsandbytes`
and `accelerate` missing from the sidecar `.venv`) is closed. The build installed both
into the sidecar venv and validated the combination end to end:

```
dev\brains\.venv\Scripts\python.exe -m pip install bitsandbytes==0.50.1 accelerate==1.14.0
```

| package | sidecar `.venv` (now) |
|---|---|
| `torch` | 2.13.0+cu126 |
| `transformers` | 5.14.1 |
| `bitsandbytes` | **0.50.1 -- INSTALLED** |
| `accelerate` | **1.14.0 -- INSTALLED** |

Verified by (all in
`IMB1_Prototype/NB08_Notebook/results/nb08_m1_wiring/`):

- `pipfreeze_before.txt` (no `bitsandbytes`/`accelerate` line) vs `pipfreeze_after.txt`
  (`accelerate==1.14.0`, `bitsandbytes==0.50.1`) -- the install landed in the sidecar
  venv, not a different interpreter.
- `armB_sidecar_bars.json`, run `"SIDECAR-ENV"`, `env.executable` =
  `dev\brains\.venv\Scripts\python.exe`, `env.torch` = `2.13.0+cu126`,
  `env.transformers` = `5.14.1`, `env.bitsandbytes` = `0.50.1` -- this is the exact
  combination this section previously called "never run anywhere in this project."
  `B1_pass: true`, `B2a_pass: true`, `B2b_pass: true`.
- `w3real_result.json` (bar `W3REAL`): `status: "PASS"`, `top1_correct: 3`,
  `prov1_ok: true` -- both stages ran in one process, in the sidecar venv, against real
  crops.

**No single interpreter on this machine had run both stages in one process before this
build; it now has, in the sidecar's own venv.**

Consequences, stated plainly:

- The dependency blocker is closed. `PILLSAFE_READER=two_stage` can load Stage 2 in the
  deployed sidecar venv today.
- Muthu still makes the arm/disarm call at CHECKPOINT 1 below -- dependency readiness is
  not the same decision as "arm for the live demo." Section 4.3's qualification-set
  caveat (the 21-image qualification run was measured with the reader disarmed) is the
  stronger argument for choosing (a) for the demo itself, independent of this fix.

CHECKPOINT 1: Muthu has read the table above and has explicitly chosen ONE of:
**(a)** deploy with `PILLSAFE_READER=off` (safe, recommended for the demo, since the
image-qualification set in 4.3 was measured disarmed), or **(b)** deploy with
`PILLSAFE_READER=two_stage` now that the dependency blocker is resolved. **Do not
proceed without that decision.**

### 1.2 -- Stage 2 model weights present

```powershell
# [LAPTOP]
Get-ChildItem "$env:USERPROFILE\.cache\huggingface\hub\models--Qwen--Qwen3-VL-4B-Instruct\snapshots" -Recurse -Filter *.safetensors | Select-Object Name, @{n='GB';e={[math]::Round($_.Length/1GB,2)}}
```

CHECKPOINT 2: two shards, `model-00001-of-00002.safetensors` (~4.97 GB) and
`model-00002-of-00002.safetensors` (~3.91 GB), ~8.3 GB total. **VERIFIED PRESENT
2026-08-14.** These are bf16 weights; NF4 quantization happens at load time, which is
why `bitsandbytes` is required at runtime and not at download time. Nothing to download.

### 1.3 -- Stage 1 Ollama fallback tag present

```powershell
# [LAPTOP]
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

CHECKPOINT 3: `qwen3-vl:latest` (6.1 GB -- the 8.8B Stage-1 incumbent) and
`qwen2.5:7b-instruct` (4.7 GB -- Rx extraction, unrelated to M1 but shares the GPU)
both listed, and the version call returns JSON. **VERIFIED PRESENT 2026-08-14.**

> **`PILLSAFE_STAGE1=ollama` is NOT a way to avoid `bitsandbytes`.** Read
> `production_wiring.build_reader`: the `ollama` branch still calls
> `scorer or get_scorer()`, because Stage 1 is a kill-only screen and **Stage 2 always
> loads the NF4 scorer either way**. Switching Stage 1 to Ollama changes which
> instrument answers the presence gate; it does not remove the 4-bit model from the
> process. The only knob that avoids the scorer entirely is `PILLSAFE_READER=off`.

### 1.4 -- Ollama keep-alive task healthy

```powershell
# [LAPTOP]
Get-ScheduledTask -TaskPath '\PillSafe\' -TaskName 'OllamaHealthCheck' | Select-Object TaskName, State
Get-Content D:\Projects\PillSafe\ops\ollama_healthcheck.log -Tail 5
```

CHECKPOINT 4: State is `Ready` (or `Running`). The log is **silent when healthy** --
one line per intervention only, so a short or stale log is the good outcome. **Do not
stop Ollama at any point in this guide**: the sidecar's Rx extraction (`/rx/extract`)
needs it live, and so does `PILLSAFE_STAGE1=ollama` if chosen.

### 1.5 -- Take the rollback snapshot (MANDATORY, before any file changes)

```powershell
# [LAPTOP]
$STAMP = Get-Date -Format "yyyyMMdd-HHmm"
$SNAP  = "D:\Projects\PillSafe\ops\snapshots\pre-M1-$STAMP"
New-Item -ItemType Directory -Force -Path $SNAP | Out-Null
Copy-Item D:\Projects\PillSafe\PillSafe\dev\brains\*.py $SNAP -Force
Copy-Item D:\Projects\PillSafe\IMB1_Prototype\NB08_Notebook\src\*.py "$SNAP\nb08_src\" -Force -Recurse
Write-Host "Snapshot: $SNAP"
```

**Record `$SNAP`** -- it is the rollback handle, the sidecar equivalent of `$TAG` in
`DEPLOY_GUIDE.md` section 4. Also capture the current git state as a second handle:

```powershell
# [LAPTOP]
cd D:\Projects\PillSafe\PillSafe
git rev-parse HEAD
git status --short dev/brains
```

CHECKPOINT 5: the snapshot directory exists and contains the `dev/brains` `.py` files;
the commit SHA is recorded. **Note that `IMB1_Prototype/NB08_Notebook/src/` and `BB3/`
are not reliably in the app repo's git history** -- for those the file snapshot is the
only rollback record, which is exactly why step 1.5 is mandatory rather than advisory.

---

## 2. Deploy to the laptop sidecar

### 2.1 -- Warn that the site is about to lose its brains

Stopping the sidecar takes pill scan, Rx scan and Q&A down at `mypillsafe.ca` until it
is back. Landing, about pages, login and register keep working (verified degradation
behaviour, `DEPLOY_GUIDE.md` section 10.1). Get Muthu's go-ahead on the timing.

### 2.2 -- Stop the sidecar

The sidecar is **not** a terminal you can Ctrl-C -- it runs under Task Scheduler so it
survives the session that started it.

```powershell
# [LAPTOP]
schtasks /end /tn "MyPillSafe Sidecar"
Start-Sleep -Seconds 3
Get-NetTCPConnection -LocalPort 8100 -State Listen -ErrorAction SilentlyContinue
```

CHECKPOINT 6: the `Get-NetTCPConnection` call returns **nothing**. If port 8100 is still
held, the old process is alive and step 2.5 will silently no-op -- see the trap in 2.5.

### 2.3 -- Update the files

There is **no file copy step.** The sidecar imports the working tree directly --
`IMB1_Prototype/NB08_Notebook/src/` is appended to `sys.path` at import time (see the
warning box below) and `dev/brains/` runs in place. The prototype tree on the laptop
**is** the deployed code; "updating the files" means the working tree already reflects
the build's changes before 2.2 stops the sidecar.

| file | change | promoted from |
|---|---|---|
| `IMB1_Prototype/NB08_Notebook/src/nb08_constrained_score.py` | new `generate_presence` (Stage 2 scorer answers the presence gate too, `_a3_prefix`) | NB08 prototype (in place, no promotion) |
| `IMB1_Prototype/NB08_Notebook/src/nb08_imb1.py` | new `_m0_render`, `write_face_crop` | NB08 prototype (in place, no promotion) |
| `dev/brains/app.py` | reader wiring on `/pill/analyze`; `ReaderError` retry mapped to `422 READER_ERROR_RETRYABLE`; `/health` gains a `reader` block including `stage2_deps_ok` | app-side, edited directly |
| `dev/brains/production_wiring.py` | reader wiring (`build_reader`, `get_scorer`, `reader_backend_report`) | app-side, edited directly |
| `dev/brains/config.py` | `PILLSAFE_READER` / `PILLSAFE_STAGE1` / `PILLSAFE_SCORER_DEVICE` knobs | app-side, edited directly |

No other files are part of this deploy's surface.

> **Do not `git pull` the NB08 prototype into the sidecar's path.** `production_wiring.py`
> APPENDS `NB08_Notebook/src` to `sys.path`, never inserts at 0 -- that directory
> contains `colour.py`, which shadows the third-party `colour-science` package that
> `IMB1_v0` imports mid-pipeline for a non-neutral pill. Inserting it first turned a
> working `analyze_pill()` into `AttributeError: module 'colour' has no attribute
> 'CCS_ILLUMINANTS'`. Preserve the append.

### 2.4 -- Set the environment knobs

**Confirmed against `dev/brains/config.py` 2026-08-14** -- three knobs, no more:
`PILLSAFE_READER` (default `off`), `PILLSAFE_STAGE1` (default `single`),
`PILLSAFE_SCORER_DEVICE` (default `cuda`). These are the exact names and defaults read
by `config.py` lines 61, 84, 89. The build validated `PILLSAFE_STAGE1=single` /
`PILLSAFE_SCORER_DEVICE=cuda` against the sidecar venv (section 1.1, `armB_sidecar_bars.json`
/ `w3real_result.json`).

The task launches `start_sidecar.cmd`, so variables must be set where that script sees
them. **As of 2026-08-14 `start_sidecar.cmd` sets no environment variables** -- it only
`cd`s into `dev/brains` and invokes `python.exe -m uvicorn`. Add `set` lines **between
the `cd /d ...` line and the `python.exe -m uvicorn ...` line** (i.e. right before the
line that launches uvicorn), so the deployed configuration is readable in one file
rather than hidden in the registry.

**Option (a), the safe deploy -- reader disarmed:**

```
set PILLSAFE_READER=off
```

or simply set nothing: `off` is the default.

**Option (b), reader armed** -- only after CHECKPOINT 1 chose (b) AND section 2.6 passed:

```
set PILLSAFE_READER=two_stage
set PILLSAFE_STAGE1=single
set PILLSAFE_SCORER_DEVICE=cuda
```

**Confirmed 2026-08-14: no additional knob.** `dev/brains/config.py` defines exactly the
three `PILLSAFE_*` variables above -- no crop-dump-directory, model-override, or timeout
env var was introduced by this build.

### 2.5 -- Start the sidecar

```powershell
# [LAPTOP]
schtasks /run /tn "MyPillSafe Sidecar"
Start-Sleep -Seconds 10
Get-Content D:\Projects\PillSafe\logs\sidecar.log -Tail 15
schtasks /query /tn "MyPillSafe Sidecar" /v /fo LIST | Select-String "Last Result"
```

CHECKPOINT 7: a **fresh** `---- sidecar start <date> <time> ----` banner with today's
timestamp, and `Last Result: 0`.

> **`schtasks /run` SILENTLY NO-OPS if the old instance still holds port 8100.** It
> reports `Last Result: 1` and starts nothing -- so a change you believe you deployed is
> still not live, and the site keeps answering from the old code. A new banner is the
> only proof of a real restart. If you get `Last Result: 1`, go back to 2.2.

First start is slow: it loads the appearance reference and opens the BB3 store. With
`PILLSAFE_READER=two_stage` it does **not** load the 4-bit model at startup -- the
scorer is lazy and loads on the first request that needs it, so a healthy `/health`
does not by itself prove the reader works. That is what 2.6 is for.

### 2.6 -- Verify health, then ONE real analyze

```powershell
# [LAPTOP]
Invoke-RestMethod http://127.0.0.1:8100/health | ConvertTo-Json -Depth 4
```

CHECKPOINT 8: `imb1_ok: true`, `sb2_ok: true`, `reference_rows` a number (7055 at the
last recorded deploy), `ocr_worker: "present"`, `torch_cuda_available: true`.

> **RESOLVED 2026-08-14: `/health` now reports reader state.**
> `production_wiring.reader_backend_report()` (`reader_enabled`, `reader_mode`,
> `stage1_backend`, `scorer_device`, `scorer_loaded`, `scorer_load_error`,
> `verify_session_import_error`) is wired into the `/health` response under a `reader`
> key, with one field added at the `app.py` level: `stage2_deps_ok` (`_stage2_deps_ok()`
> in `app.py`, an `importlib.util.find_spec` check for `transformers`, `bitsandbytes`,
> `accelerate` -- `True`, or a `"missing: ..."` string). Confirmed by reading
> `dev/brains/app.py` (`health()`, the `"reader"` key) and
> `dev/brains/production_wiring.py` (`reader_backend_report()`). This is a
> **configuration report, not a probe** -- it never loads the 4-bit scorer, so a healthy
> `reader.scorer_loaded: false` at startup is expected (the scorer loads lazily on first
> request); the live analyze below is still the only proof the request path works.

Then the load-bearing test -- one real pill through the real path:

```powershell
# [LAPTOP]
$img = "D:\Projects\PillSafe\archive\demoprep\images\motrin\DIN02242658_DarkGrey_ColourRef_Front_DL.jpg"
curl.exe -s -X POST http://127.0.0.1:8100/pill/analyze `
  -F "image=@$img" `
  -F 'profile_dins=["DIN02242658","DIN02237726"]'
```

CHECKPOINT 9: JSON returns with `record.detected: true` and
`match.decision: "verify"`, `match.matched_din` resolving to DIN2242658.

- With the reader **armed**, the record should additionally carry `contract_version:
  "C6"` and a populated `faces[]`. **Confirmed 2026-08-14** by reading
  `dev/brains/production_wiring.py`: `contract_version` is literally the string `"C6"`
  (see the module docstring's `sb2.match_pill` branch,
  `record.get("contract_version") == "C6"`), and `faces` is the key name (not
  `faces_out` or similar) -- both key names are exact.
- With the reader **disarmed**, the record is the legacy shape (`colour_modes`,
  `shape_out`, `imprint_reads`, no `faces`) -- that is correct, not a failure.

**If this call errors with anything mentioning `bitsandbytes`, `accelerate`,
`load_in_4bit` or `quantization_config`, section 1.1's blocker is live.** Go straight to
rollback option R1 (section 5) -- set `PILLSAFE_READER=off` and restart. Do not attempt
to install packages into the sidecar venv while the site is down.

---

## 3. The droplet: NO CHANGE REQUIRED

**Verified 2026-08-14 by reading the code, not assumed.** No image rebuild, no push, no
`IMAGE_TAG` bump, no compose edit, no `git pull` on the droplet.

**Why the droplet does not need rebuilding:**

1. **The brains are not in any image.** `dev/backend/Dockerfile` builds from the
   `dev/backend` context (`COPY . .` at line 49) and `dev/frontend/Dockerfile` from
   `dev/frontend`. Neither context contains `dev/brains/`, `IMB1_v0/`, `SB2/`, `BB3/` or
   `IMB1_Prototype/`. Nothing M1 changes is inside an image.

2. **The backend is a thin proxy.** `dev/backend/app/api/v1/routes/pill.py`
   (`POST /analyze/pill/v2`) resolves a sidecar URL from the `BRAINS_SERVICE_URLS` pool,
   POSTs the image and `profile_dins` to `<sidecar>/pill/analyze`, and returns
   `{"status": "ok", "record": record, "match": enriched_match}`.

3. **`record` is passed through opaquely and unvalidated.** The route has **no
   `response_model`**, and `record` is forwarded as-is from the sidecar. New C6 fields
   (`contract_version`, `faces[]`) therefore reach the SPA with no backend change. The
   backend reads only two keys out of it -- `record.get("detected")` and
   `record.get("shadow_fusion_suspected")`, both persisted to the `Analysis` row.

4. **The frontend ignores unknown fields.** `PillRecord` in
   `dev/frontend/src/types/index.ts` is a compile-time TypeScript interface with no
   runtime validation; extra JSON keys are simply unread. `PillResultPanel.tsx` and
   `AnalyzePage.tsx` consume only `record.detected`, `record.shadow_fusion_suspected`,
   and `match.{decision, matched_din, abstain_action, ranked_candidates}`. **A C6 record
   renders correctly on the currently-deployed SPA build.**

**Two contract invariants M1 must not break** -- if the build violated either, the
droplet DOES need a rebuild and this section is void:

| invariant | where it bites | symptom if broken |
|---|---|---|
| `record` keeps a top-level `detected` boolean | `pill.py:192`, `PillResultPanel.tsx:120`, `AnalyzePage.tsx:152` | every scan renders as "no pill detected" |
| `match.ranked_candidates` stays a list of **>=3-element sequences** `[token, score, breakdown]` | `pill.py:_enrich_ranked_candidates` indexes `item[0]`, `item[1]`, `item[2]`; `item[0]` also feeds the reference lookup | `TypeError`/`KeyError` -> 500 on every scan. **Changing these to dicts is a breaking change requiring a backend rebuild and redeploy.** |

**Confirmed 2026-08-14, both invariants hold.** `detected` stays a top-level boolean --
read `IMB1_Prototype/NB08_Notebook/src/nb08_imb1.py`, where
`PillRecord(detected=False, ...)` and `detected=True` are set exactly as before; the
M1 changes to that file (`_m0_render`, `write_face_crop`) are additive and do not touch
this field. `ranked_candidates` is untouched -- it is produced by `sb2.match_pill` and
consumed by `dev/backend/app/api/v1/routes/pill.py`'s `_enrich_ranked_candidates`
(`item[0]`, `item[1]`, `item[2]`), neither of which is in this build's changed-file list
(section 2.3). Since M1's surface is `nb08_constrained_score.py`, `nb08_imb1.py`,
`app.py`, `production_wiring.py` and `config.py` only, the matching/candidate-ranking
code path this invariant depends on was not touched.

**The one droplet-side action, and it is a check, not a change** -- confirm the live
backend still reaches the restarted sidecar:

```bash
# [DROPLET]
sudo docker exec pillsafe_backend python -c "import httpx; print(httpx.get('http://<LAPTOP_TS_IP>:8100/health', timeout=5).status_code)"
```

CHECKPOINT 10: prints `200`. This is `DEPLOY_GUIDE.md`'s CHECKPOINT 11 re-run, and it
is required after **every** sidecar restart. `<LAPTOP_TS_IP>` is the raw `100.x.y.z`
tailnet address -- it is recorded in two places and nowhere else: the `--host` argument
in `D:\Projects\PillSafe\ops\start_sidecar.cmd`, and `BRAINS_SERVICE_URLS` in
`/opt/mypillsafe/repo/.env` on the droplet. **Never a MagicDNS hostname** -- containers
use Docker's resolver and will not resolve tailnet names.

---

## 4. Live-demo provisioning at mypillsafe.ca

The demo assets in `D:\Projects\PillSafe\archive\demoprep\` were built and measured
against **localhost with an isolated throwaway SQLite database**. Production is Postgres
with `REQUIRE_ADMIN_APPROVAL=true` and `APP_ENV=production`. The gap is real and every
item below is gated on Muthu.

> **`POST /dev/seed-admin` returns 404 in production** (`dev.py:23` -- guarded on
> `APP_ENV != "development"`). The localhost recipe in `DEMO_RUNBOOK.md` section 1 and
> `04_users.md` **cannot be run against mypillsafe.ca.** Every account must go through
> register -> admin-approve instead.

### 4.1 -- Demo accounts (NEEDS PROVISIONING -- Muthu executes)

The three demo patients (`demo.margaret.chen@`, `demo.arthur.chen@`,
`demo.priya.nadarajah@`, roster in `archive/demoprep/users/demo_users.csv`) exist in
**no** database -- not even Muthu's local `pillsafe.db`; `04_users.md` records they were
only ever created in a temporary throwaway DB on port 8199, then cleaned up.

There is **no seed script for production.** Provision each one by hand:

1. Muthu confirms he is already an admin on prod (`ADMIN_EMAILS` promotion, see
   `DEPLOY_GUIDE.md` section 7.2a). If not, do that first -- it is the only route in.
2. **Muthu executes:** register each of the three patients at
   `https://mypillsafe.ca/register` using the emails and password in `demo_users.csv`.
   Each lands on the "awaiting approval" screen -- correct, not an error.
3. **Muthu approves:** Admin -> Users, approve all three (amber *Pending approval*
   badge, **Approve** button).
4. Verify each can log in and reaches `/dashboard`.

CHECKPOINT 11: all three demo patients log in successfully on the live site.

> **Muthu approves the cost first.** These are real accounts on a public site that can
> spend Anthropic tokens through the Q&A brain. Confirm the spend cap in the Anthropic
> console before creating them.

### 4.2 -- Prescriptions (EXISTS as files, NEEDS UPLOADING -- Muthu executes)

`RX_DEMO_MargaretChen.jpg`, `RX_DEMO_ArthurChen.jpg`, `RX_DEMO_PriyaNadarajah.jpg` in
`archive/demoprep/prescriptions/` are OCR-verified inputs, each with a saved
`_ocr.json` and `_extract.json`. They are **files, not production state** -- nothing to
migrate. For each patient: log in, `/dashboard/scan-prescription`, upload the JPG, then
confirm each suggested DIN and approve the medication at `/dashboard/medications`.

**This step is not optional and it is the demo's real dependency:** `analyze_pill_v2`
short-circuits to `no_profile` and never calls the sidecar unless the patient has at
least one ACTIVE prescription with `din_confirmed` set. **No confirmed DIN, no pill
scan.** Do this before the recording, not during it.

CHECKPOINT 12: Margaret's profile shows 4 approved medications with confirmed DINs
(DIN2242658, DIN2237726, DIN2230790, DIN13803).

### 4.3 -- Pill images (EXISTS as files, uploaded live)

21 qualifying images across 8 DINs sit in `archive/demoprep/images/<product>/`
(advil 2, asa.81 4, benadryl 2, gravol 3, motrin 2, naproxen 4, senekot.s 2, tylenol 2).
They are uploaded live through the browser; nothing is pre-staged server-side.

> **`muscle.back` (DIN2230790) has ZERO qualifying images** -- 0 of 12 variants reached
> `verify`. Do not plan a demo beat on it; `DEMO_RUNBOOK.md` section 2 step 8 already
> handles this with a narrated substitution.

> **WARNING -- the qualification numbers were measured with the reader DISARMED.** All 21
> qualifying results in `02_image_qualification.md` came through the legacy
> `imb1.analyze_pill` path. **If you deploy with `PILLSAFE_READER=two_stage`, that
> qualification set is no longer evidence** -- the decision path changed underneath it.
> Either demo with the reader off, or re-qualify at least Margaret's two images against
> the armed sidecar before recording. This is the strongest practical argument for
> choosing option (a) in CHECKPOINT 1 for the demo itself.

### 4.4 -- File-upload fallback on the prod build (EXISTS IN PROD)

`CameraCapture.tsx` renders a `<input type="file" accept="image/*">` picker
**unconditionally**, in both the pre-capture and the live-viewfinder states -- it is not
gated on `getUserMedia` failing. On desktop this is exactly the "plain file picker"
`DEMO_RUNBOOK.md` assumes. The live site is HTTPS, so the secure-context requirement
for `getUserMedia` is satisfied and the camera path also works. **No change needed.**

CHECKPOINT 13: on `https://mypillsafe.ca/dashboard/scan-pill`, the file-picker control
is visible and selecting a local JPG produces a preview.

### 4.5 -- Before the recording

From `DEPLOY_GUIDE.md` section 12, unchanged and still mandatory:

```powershell
# [LAPTOP - ADMIN]
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
```

Then **warm the models** -- one throwaway Rx scan, one pill scan, one Q&A. With the
reader armed the first pill scan additionally pays the 4-bit model load into an 8.6 GB
card. Nobody should watch that on camera.

---

## 5. Rollback

Three levels, cheapest first. **R1 is almost always the right answer.**

**R1 -- Disarm the reader (seconds, no file changes).** The reader is a config switch,
which is the entire point of its design. Set `PILLSAFE_READER=off` in
`start_sidecar.cmd`, then:

```powershell
# [LAPTOP]
schtasks /end /tn "MyPillSafe Sidecar"
Start-Sleep -Seconds 3
schtasks /run /tn "MyPillSafe Sidecar"
Get-Content D:\Projects\PillSafe\logs\sidecar.log -Tail 5
```

The sidecar returns to byte-identical pre-M1 behaviour. Verify with CHECKPOINT 9
(expect a legacy-shape record) and CHECKPOINT 10.

**R2 -- Swap Stage 1 to the 8.8B incumbent.** Only for a Stage-1-specific regression
(presence gate wrongly killing reads). Set `PILLSAFE_STAGE1=ollama` and restart as
above. **This does NOT avoid the NF4 scorer** -- see the box in 1.3. If the failure is
`bitsandbytes`, R2 will not help; use R1.

**R3 -- Restore the file snapshot.** For an actual code regression:

```powershell
# [LAPTOP]
schtasks /end /tn "MyPillSafe Sidecar"
Copy-Item "<SNAP>\*.py" D:\Projects\PillSafe\PillSafe\dev\brains\ -Force
Copy-Item "<SNAP>\nb08_src\*.py" D:\Projects\PillSafe\IMB1_Prototype\NB08_Notebook\src\ -Force
schtasks /run /tn "MyPillSafe Sidecar"
```

`<SNAP>` is the path recorded at CHECKPOINT 5.

**There is no droplet rollback**, because there was no droplet change. If a droplet
rollback is ever needed, it is `IMAGE_TAG` -> previous tag per `DEPLOY_GUIDE.md`
section 12, and it means section 3's no-change verdict was wrong.

---

## 6. Verify after deploy

Work down the list. Do not sign off early -- the last row is the one that matters.

| # | Check | Where | Expected |
|---|---|---|---|
| 1 | Fresh sidecar banner + `Last Result: 0` | [LAPTOP] | new timestamp (CHECKPOINT 7) |
| 2 | `/health` | [LAPTOP] | `imb1_ok`/`sb2_ok` true, `reference_rows` numeric, `ocr_worker: present`, `torch_cuda_available: true` |
| 3 | Reader state reported | [LAPTOP] | `GET /health` -> `reader` key present with `reader_enabled`, `reader_mode`, `stage1_backend`, `scorer_device`, `scorer_loaded`, `scorer_load_error`, `verify_session_import_error`, `stage2_deps_ok: true` |
| 4 | **WARM-UP:** fire one throwaway `/pill/analyze` | [LAPTOP] | do this **before** anything else below or any live demo step -- cold first request measured 43.43 s (`w3real_result.json`, `cold_total_s`) vs 8.58-10.08 s warm (`warm_min_s`/`warm_max_s`, median 9.33 s). Nobody should watch the cold load on camera |
| 5 | One real `/pill/analyze` | [LAPTOP] | `detected: true`, `decision: verify` (CHECKPOINT 9) |
| 6 | Container reaches sidecar | [DROPLET] | `200` (CHECKPOINT 10) |
| 7 | Neighbours unaffected | [DROPLET] | JAcI + PathoIntern healthy; `curl http://127.0.0.1:80` returns `301` |
| 8 | Ollama still up | [LAPTOP] | `ollama list` responds; healthcheck log silent |
| 9 | Degradation still clean | both | stop the sidecar: public pages work, pill/Rx/Q&A give clear service-unavailable, **never fabricated text**. Restart, confirm recovery |
| 10 | **LIVE SMOKE at `https://mypillsafe.ca`** | browser | log in as a demo patient -> `/dashboard/scan-pill` -> upload `images/motrin/DIN02242658_DarkGrey_ColourRef_Front_DL.jpg` -> **green `verify`, DIN2242658**. Then a deliberate wrong pill -> **red `reject`**. Then an ambiguous one -> **amber `abstain`, never styled red or green** |

CHECKPOINT 14: row 10 passes on the live site. **The deploy is not done until a real
pill verifies through `https://mypillsafe.ca` in a browser.** Everything above it is
necessary and none of it is sufficient.

---

## 7. Triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `schtasks /run` -> `Last Result: 1`, no new banner | old instance still holds :8100 | re-run 2.2, confirm the port is free, then 2.5 |
| Scan errors mention `bitsandbytes` / `load_in_4bit` / `quantization_config` | deps are installed (section 1.1, resolved) but something in the loaded environment regressed -- check `/health`'s `reader.stage2_deps_ok` first | R1 (`PILLSAFE_READER=off`) + restart. Do not pip-install with the site down |
| Scans 500 with `TypeError`/`KeyError` on an index | `ranked_candidates` shape changed | section 3 invariant broken -- R3, and the droplet needs a rebuild |
| Every scan says "no pill detected" | `record.detected` missing from the C6 record | section 3 invariant broken -- R3 |
| Pill/Rx/Q&A all 503 at mypillsafe.ca | sidecar down, laptop asleep, or wrong IP in `BRAINS_SERVICE_URLS` | CHECKPOINT 10; check laptop sleep (4.5) |
| First scan very slow, later ones fine | lazy 4-bit model load on first request | expected -- warm the models before any demo (4.5) |
| CUDA OOM on first armed scan | 4-bit VLM + Ollama models competing for 8.6 GB | `ollama stop qwen3-vl:latest` before an armed scan, or R1 |
| Pill scan returns `no_profile` | patient has no confirmed-DIN active prescription | section 4.2 -- the sidecar was never called; this is not a sidecar fault |
| `/dev/seed-admin` 404 on prod | by design, `APP_ENV=production` | use register + Admin -> Users approve (4.1) |

---

## 8. Deliberately out of scope

- Installing `bitsandbytes`/`accelerate` into the sidecar venv as an ad hoc step during
  this deploy. **This is now moot -- RESOLVED 2026-08-14, see section 1.1**: the install
  already happened as its own verified change (`bitsandbytes==0.50.1`,
  `accelerate==1.14.0`), with its own testing (`armB_sidecar_bars.json`,
  `w3real_result.json`), before this guide was finalized.
- The app-photo calibration gap (`production_wiring.py` docstring: a legacy record never
  reaches SB2's C6 branch, so the map is reachable but not yet effective on real
  photographed pills). Build spec section 8 open item 9.
- Dose-schedule enforcement (Futureworks #24) -- narrated as a gap in the demo, not
  built.
- Any droplet change. If one becomes necessary, `DEPLOY_GUIDE.md` is the authority.
