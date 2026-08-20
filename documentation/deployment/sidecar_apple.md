# Sidecar on Apple Silicon — feasibility brief

**Target hardware:** MacBook Pro, Apple M1 Pro, 32 GB unified memory.
**Question this document answers:** can the PillSafe brains sidecar be deployed on it?
**Status: ANALYSIS BRIEF — nothing built, nothing ported.**

**🔵 DECIDED (Muthu, 2026-08-13): the Mac is a SECOND NODE, not a replacement.** The
RTX 4060 laptop stays the measurement instrument of record. This decision is what §9–§11
are written against — read §9 first, because the multi-node pool it describes **already
exists in the backend** and it changes the acceptance bar from what a naive "does it
run" port would assume.

Everything below was read out of the code and the filesystem on 2026-08-13, not from
project memory. Every claim carries its source file and line. Items marked
**🔶 UNVERIFIED** are the ones the reader is being handed: they are unresolved because
they need a network check or a Mac, not because they were skipped.

**Current sidecar host:** Windows 11, RTX 4060 (8 GB VRAM), CUDA 12.6, Python 3.12.
**Verdict as it stands: 🟡 PARTIAL** — memory and disk are comfortable, the blockers are
all in the dependency stack and the device-selection code, and the frozen accuracy
numbers do not transfer for free (§7).

---

## 1. What "the sidecar" is

One `uvicorn` process plus per-call subprocesses plus a local Ollama server:

```
ops/start_sidecar.cmd
  └─ python -m uvicorn app:app --host 100.119.95.105 --port 8100   ← holds torch
       ├─ subprocess: python -m imb1.ocr_sub        (paddle only, per pill call)
       ├─ subprocess: python rx_ocr_sub.py          (paddle only, per Rx call)
       └─ HTTP → http://localhost:11434             (Ollama, qwen2.5:7b-instruct)
```

Three of the five brains run here. **SB2** is pure CPU arithmetic with no ML framework.
**CB4** is cloud (`claude-haiku-4-5` over HTTPS) and is not part of this port.

**🔴 Do not "simplify" the two-process split.** torch and paddle cannot share one
Windows process (`WinError 127`, diagnosed 2026-07-09) — that is why OCR is a
subprocess. The DLL conflict is Windows-specific and *may* not exist on macOS, but
`IMB1_v0/CONTRACT.md` marks the split as a do-not-fix constraint and the subprocess
design is also what keeps the paddle import out of the torch process. Merging them is
out of scope for a port; it is a separate, re-measured change.

Sources: `dev/brains/app.py:20-24`, `IMB1_v0/imb1/__init__.py:31-42`,
`IMB1_v0/imb1/ocr_sub.py:1-9`, `ops/start_sidecar.cmd`.

---

## 2. Compute inventory — every model that loads

| Brain | Component | Framework | Weights on disk | Device selection |
|---|---|---|---|---|
| **IMB1** | FastSAM-x detect, `imgsz=1024`, `retina_masks=True`, `conf=0.4`, `iou=0.9` | ultralytics 8.4.90 / torch | `IMB1_v0/models/FastSAM-x.pt` — 144,972,346 B (**138.3 MiB**) | `pipeline.py:71` — `FastSAM(weights)`, **no device argument**; inference call `pipeline.py:155` also passes none → ultralytics auto-select |
| **IMB1** | S2 shape CNN — ResNet18, 8 classes, 224 px letterbox | torch / torchvision | `s2_shape_cnn_best.pt` — 44,803,211 B (**42.7 MiB**) | `pipeline.py:79` — `"cuda" if torch.cuda.is_available() else "cpu"` |
| **IMB1** | Colour — card white-balance → CIELAB → 13-class | numpy, opencv, scikit-image, scikit-learn | none — **never learned** | CPU by construction |
| **IMB1** | Imprint dual-read I1 (zero-shot) + I3 (CLAHE) | PaddleOCR 3.7.0 | `~/.paddleocr` 222 MiB + `~/.paddlex` 269 MiB (**≈491 MiB**): PP-OCRv5/v6 det + rec, PP-LCNet doc-ori + textline-ori | subprocess (`imb1/__init__.py:37`). **Model is constructed fresh on every call** — no persistent worker, by design (`ocr_sub.py:100`) |
| **OB5** | Prescription OCR | PaddleOCR (same cache) | shared with above | subprocess `app.py:256`, `timeout=300` |
| **OB5** | Rx proposer — `temperature 0`, `num_ctx 8192`, `format: json` | Ollama | `qwen2.5:7b-instruct` — 4,683,073,952 B (**4.36 GiB**, Q4) | `rx_extract.py:48` (`RX_LLM_MODEL`), `:57` |
| **SB2** | Deterministic matcher | rapidfuzz, pandas, openpyxl — **no torch** | `SB2/data/ca_appearance_harmonized_v2.xlsx` — 1,582,871 B (**1.51 MiB**) | CPU only; has no device concept |
| **BB3** | Query embedder | sentence-transformers | `BAAI/bge-small-en-v1.5`, **384-dim** | `retrieve.py:59` — `"cuda" if torch.cuda.is_available() else "cpu"` |
| **BB3** | Store — SQLite FTS5 + flat float32 memmap | numpy / sqlite3 | `bb3.db` 2,646,904,832 B (**2.47 GiB**) + `embeddings.f32` 6,014,141,952 B (**5.60 GiB**) = **8.07 GiB**; 3,915,457 × 384 × f32 | CPU. Never fully loaded — `retrieve.py:248` fancy-indexes only candidate rows |
| **BB3** | Offline fallback voice | Ollama | **same** `qwen2.5:7b-instruct` — one model load serves both OB5 and BB3 | `engine.py:33`, `NUM_CTX = 8192` at `engine.py:30` |
| **CB4** | Production voice | Anthropic HTTPS | none local | not part of this port |

### Retrieval I/O shape (matters for a laptop SSD)

`bb3/retrieve.py:243-250` collects candidate `emb_row` indices from SQLite, then does
`mm[emb_rows]` against the 5.60 GiB memmap — a **random-access gather**, not a scan.
Worst case measured in the code comments (`retrieve.py:42-46`): hydrochlorothiazide,
191 DINs → 103,384 candidate chunks → **151.4 MiB** gathered per query. Apixaban, 44
DINs → 37,524 chunks. Any NVMe handles this; a network volume would not.

---

## 3. Resource budget

**Disk**

| Item | Size |
|---|---|
| BB3 store (`bb3.db` + `embeddings.f32`) | 8.07 GiB |
| Ollama `qwen2.5:7b-instruct` | 4.36 GiB |
| PaddleOCR / PaddleX model caches | ≈0.48 GiB |
| IMB1 weights (`models/`) | 0.18 GiB |
| SB2 reference workbook | 0.002 GiB |
| Python venv (torch + paddle + sentence-transformers) | ≈5–7 GiB |
| **Total** | **≈19–21 GiB** |

Note: the current laptop's `~/.ollama/models` is 21 GiB total, but that includes
`llama3`, `mistral`, `qwen2.5:3b-instruct` and `qwen3-vl` — **none of which the sidecar
uses**. Only `qwen2.5:7b-instruct` is needed.

**Memory** — this is where the M1 Pro is *better than the current host*, not worse.
The RTX 4060's 8 GB VRAM is the present binding constraint; the project's standing ops
rule is *"qwen holds ~4.9 GB — never run a CUDA job concurrently with a qwen harness"*
(that contention produced a discarded empty-response measurement run). On 32 GB unified
memory, **that constraint disappears**. Expected steady state: ~4.9 GiB resident in
Ollama, plus the torch process (FastSAM-x + ResNet18 + bge-small), plus a transient
paddle subprocess. There is headroom.

---

## 4. The porting surface — device selection

The whole codebase selects a device in **three places**, and all three are binary:

| File | Line | Code |
|---|---|---|
| `IMB1_v0/imb1/pipeline.py` | 79 | `dev = "cuda" if torch.cuda.is_available() else "cpu"` |
| `BB3/bb3/retrieve.py` | 59 | `device = "cuda" if torch.cuda.is_available() else "cpu"` |
| `BB3/bb3/export_store.py` | 206 | same (one-time export job — already run, not on the runtime path) |

**There is no `torch.backends.mps` test anywhere in `IMB1_v0/`, `SB2/`, `BB3/bb3/` or
`dev/brains/`.** Verified by grep across all four packages, 2026-08-13.

**Consequence:** on an M1, S2 shape and the bge-small embedder run **CPU-only** and the
Mac's 16-core GPU sits idle for them. FastSAM is the one exception — it is constructed
with no device argument (`pipeline.py:71`), so ultralytics' own auto-selection decides.
🔶 **UNVERIFIED:** whether ultralytics 8.4.90's `select_device` falls through to MPS on
Apple Silicon when CUDA is absent. Check this first — it determines whether the heaviest
vision model gets GPU acceleration for free or needs a code change.

Also note `dev/brains/app.py:190` reports `torch_cuda_available` in `GET /health`. On a
Mac this will report `false`. **That is expected and is not a failure** — do not treat it
as a broken deploy. It does mean the current health endpoint gives you no signal about
whether MPS is in use; adding that is a reasonable first patch.

---

## 5. Blockers

### B1 — `paddlepaddle-gpu==3.3.1` cannot install on Apple Silicon 🔴 HIGHEST RISK

`dev/brains/requirements.txt:23` and `IMB1_v0/requirements.txt:16` both pin
`paddlepaddle-gpu==3.3.1` from the CUDA 12.6 index. There is no CUDA on macOS; this must
become the CPU `paddlepaddle` arm64 wheel.

This is the highest-risk item because PaddleOCR is load-bearing for **both** OB5
(prescription reading) and IMB1's imprint read — and **imprint causes 83.9% of IMB1's
non-verifications**. If no compatible macOS arm64 wheel exists, the port stops here.

🔶 **UNVERIFIED:** availability and version of a macOS arm64 `paddlepaddle` wheel
compatible with `paddleocr==3.7.0`.

### B2 — CUDA-tagged torch pins

`torch==2.13.0+cu126` / `torchvision==0.28.0+cu126` (`requirements.txt:18-19`) are
CUDA-suffixed builds from `download.pytorch.org/whl/cu126`. On macOS these become the
plain arm64 wheels (CPU + MPS). 🔶 **UNVERIFIED:** that `torch==2.13.0` /
`torchvision==0.28.0` publish macOS arm64 wheels.

### B3 — `opencv-python==5.0.0.93` 🔶 UNVERIFIED

Pinned at `requirements.txt:15` alongside `opencv-contrib-python==4.10.0.84`. Confirm
both have macOS arm64 wheels at those exact versions before planning anything else.

### B4 — Per-call PaddleOCR model construction becomes a CPU-bound latency tax

`ocr_sub.py:100` (`dual_read`) calls `make_ocr()` on **every invocation** — there is no
persistent OCR worker, by design, and the sidecar README states this explicitly. On the
current host that cost is hidden by the GPU. On CPU it is paid in full: **twice per pill
analysis** (I1 + I3 share one constructor call, but the process itself respawns per
call) and **once per prescription scan**.

Making the worker persistent is an obvious optimization and is **out of scope for a
straight port** — it changes the frozen architecture and would need its own
measurement. Record the latency first; don't fix it in the same change.

### B5 — No non-CUDA performance measurement exists, anywhere

`IMB1_v0/README.md:65-71` is the only latency record and it is GPU-only:

> detect+shape "in well under a second per photo on GPU; PaddleOCR's two reads add
> roughly another second. CPU-only will work (all models fall back automatically) but is
> materially slower — **budget several seconds per `analyze_pill()` call on CPU,
> untested precisely in this package**."

So the honest answer to "how fast will it be on an M1" is **nobody has measured it on
any non-CUDA host**. Producing that number is the single most useful thing this analysis
can deliver. Callers are told to allow ≥180 s timeouts (`dev/brains/README.md:78`), so
there is slack — but the user-facing experience is a different bar from the timeout.

---

## 6. Checklist for the analyst

Cheap desk checks, in order — **1–3 decide whether this is a weekend port or a dead end,
and need no Mac:**

1. Does a macOS arm64 `paddlepaddle` wheel exist that satisfies `paddleocr==3.7.0`? Which version?
2. Do `torch==2.13.0` and `torchvision==0.28.0` publish macOS arm64 wheels?
3. Do `opencv-python==5.0.0.93` and `opencv-contrib-python==4.10.0.84` publish macOS arm64 wheels?
4. Does ultralytics 8.4.90 auto-select MPS when CUDA is absent? (Read `select_device`.)
5. Does `paddlepaddle` CPU on arm64 change PaddleOCR's *outputs*, or only its speed? Numerics drift here would move the imprint reads, which is the accuracy-critical channel.

Then, on the Mac:

6. Install the stack; run the sidecar's own offline suite (24 tests, no live service, no Ollama, no GPU — `dev/brains/README.md:149`).
7. `GET /health` → confirm `imb1_ok`, `sb2_ok`, `bb3_ok`, reference row counts **7,055 appearance / 11,609 profile**, `ollama_up`. Expect `torch_cuda_available: false` and treat it as normal.
8. Time `POST /pill/analyze` and `POST /ocr/prescription` end-to-end, cold and warm. Report the split between paddle subprocess spawn, model construction, and inference.
9. Confirm whether MPS is actually engaged (instrument the three device sites, or check process GPU usage).
10. Run the **Bar C equivalence checks (§10)** — paired, the same inputs through both nodes.
11. Only then add the Mac to `BRAINS_SERVICE_URLS` (§9). Adding it before equivalence is
    established puts an unvalidated instrument in the live rotation.

---

## 7. 🔴 The part that is easy to miss: a port is a re-measurement event

`dev/brains/requirements.txt:4-8` states why the heavy pins exist:

> Heavy pins mirror the known-good reference venv `IMB1_Prototype\.venv` … so the frozen
> IMB1_v0 package's model weights load against the exact framework versions they were
> **measured** with.

**The pinned stack is the measurement instrument, not just a config.** Swapping CUDA
torch for arm64 torch and paddle-GPU for paddle-CPU changes the instrument. Every IMB1
and SB2 number currently cited — detect 180/180, verify 31.1%, false-accept 1.25%
(9/720), imprint causing 83.9% of non-verifications, SB2 held-out FA 1.15% — **was
measured on the RTX 4060 and does not transfer to a different backend for free**.

This is the project's own recurring lesson applied to hardware: studio benchmarks
overstate real transfer, and it held for 2 of 2 trained heads. Assume nothing transfers
until it is re-run.

Practical implication: if the paper cites those numbers, the 4060 must remain the
instrument of record, or the numbers must be re-measured on the new host and reported as
such. Do not silently re-baseline.

---

## 8. Ops deltas

| Thing | Current (Windows) | On the Mac |
|---|---|---|
| Process supervision | Task Scheduler task **"MyPillSafe Sidecar"** → `ops/start_sidecar.cmd` | needs a `launchd` plist (or equivalent). Must survive terminal exit and be verifiable by process ancestry |
| Network binding | `--host 100.119.95.105` **hardcoded** in `start_sidecar.cmd` — Tailscale IP only, deliberately invisible on LAN/café Wi-Fi | the Mac needs its own tailnet address; the droplet's `BRAINS_SERVICE_URL` must be repointed |
| Health probe | `127.0.0.1:8100` **fails by design** — the service binds the tailnet IP only | same behaviour will reproduce; probe the tailnet IP, not loopback |
| Restart semantics | `schtasks /end` then `/run`, then **confirm a new `---- sidecar start ----` banner**. A bare `/run` silently no-ops while the old instance holds port 8100, and an orphaned listener makes `/end` return success while killing nothing | design the launchd equivalent so a failed restart is *loud*. Restarting the sidecar **is** the brain-deploy mechanism (DEPLOY_GUIDE §12) — a silent no-op means a brain change believed deployed never landed |
| Sleep | disabled on AC **and** DC | must be disabled on the Mac too, or the sidecar disappears mid-session. With a pool, a sleeping node is *tolerated* (health check fails, traffic moves) — but see §9, consequence 3: it costs a 2 s timeout per 30 s cache window if it is first in list order |
| Brain deploy | restart the one sidecar | **must hit BOTH nodes** — see §9, consequence 1. Updating one and not the other splits traffic between old and new brain behaviour, silently |
| Ollama | tray app, session-independent | Ollama on macOS runs on Metal; confirm it starts at login |

**🔴 BB3 is versioned nowhere.** Per a settled 2026-07-30 decision, BB3 is not in any
Docker image, compose file, or git repo — those 8.07 GiB exist **only on the current
laptop**, and frozen `bb3/retrieve.py` has no rollback (recovery is re-editing;
`BB3/results/` is the only pre/post record). Porting means physically copying the store
and accepting that there is now more than one unversioned copy. Plan how they stay in
sync, or declare one authoritative.

---

## 9. Second-node mode — the pool already exists

**Good news: no backend work is required.** `app/services/brains_registry.py` (Task A3)
was built for precisely this scenario. Its own docstring:

> *"up to five team members may each run a `dev/brains` sidecar on their own laptop. A
> closed laptop must not take the demo down — this module picks a healthy sidecar URL
> from a configured pool instead of hardcoding one."*

**How to turn it on:** set `BRAINS_SERVICE_URLS` (comma-separated, `config.py:87`) to
both tailnet URLs. Empty — the current setting — is the back-compat single-URL path that
returns `BRAINS_SERVICE_URL` with **no health check at all**. The pool machinery only
activates once a second URL is configured.

**Selection rules** (`brains_registry.py:75-105`):

| Rule | Behaviour |
|---|---|
| 1 | No pool configured → single URL, zero health-check latency (load-bearing back-compat) |
| 2 | Pool configured → the admin-pinned URL if pinned **and** healthy; else **the first healthy URL in list order**; else the first URL in the list |
| 4 | Never raises — any failure degrades to "first configured URL" |

Health = `GET {url}/health` returning 200, 2 s timeout, **cached 30 s per URL**
(`:30-31`). Resolution happens **once per request** (`pill.py:124`, `qa.py:80`), and both
call sites deliberately resolve once and reuse, because *"the pool could resolve to a
different URL on a second call, which would produce a misleading error."*

Admin surface: `GET /admin/brains/pool` for status, plus a pin endpoint
(`admin.py:134-158`). **The pin is process-local and not persisted** (`:36-37`) — a
backend restart or redeploy silently drops it.

### 🔴 The hazard this creates: cross-node divergence

With one node, "the sidecar" is one instrument. With two, **list order and health
flapping decide which instrument serves any given request** — and a user's two
consecutive pill scans can land on different nodes.

That matters because the Mac's stack is not the 4060's stack (§5): paddle-CPU on arm64
vs paddle-GPU on CUDA. If the imprint reads differ even slightly, the **same pill photo
can produce a different SB2 verdict depending on which node answered**. SB2's operating
point is explicitly knife-edged — `SB2/sb2/matcher.py:152` records that dropping accept
from 0.70 to 0.65 moves false-accepts from 0% to 0.58%. Small OCR deltas cross
thresholds.

A user seeing "verified" and then "couldn't verify" for the same pill, with no
explanation, is a decision-support failure even though neither node is broken. **This is
the reason the acceptance bar below is not "does it run."**

Three secondary consequences:

1. **Brain deploys must now hit BOTH nodes.** Restarting the sidecar *is* the
   brain-deploy mechanism (DEPLOY_GUIDE §12). With a pool, updating one laptop and not
   the other means a silent, roughly-half-of-requests split between old and new brain
   behaviour — with no error anywhere.
2. **Two unversioned BB3 stores can drift.** BB3 is in no image, compose file, or git
   repo; `bb3/retrieve.py` is frozen with no rollback. A fix hand-applied to one laptop
   does not reach the other, and the same question then returns different citations
   depending on routing.
3. **Enabling the pool adds latency to every request.** Rule 2 walks the list in order;
   an unhealthy first entry costs up to a 2 s health timeout (then cached 30 s) before
   the second is tried. Put the node most likely to be up **first** in
   `BRAINS_SERVICE_URLS`.

---

## 10. Acceptance bar — Bar C, node equivalence

Given the second-node decision, neither of the obvious bars is the right one:

- **Bar A ("it runs")** — suite passes, `/health` green, one photo produces a
  well-formed record. **Insufficient**: it cannot detect §9's divergence hazard at all.
- **Bar B ("the numbers hold")** — re-derive verify/false-accept rates on the 186-photo
  OTC set. **Unnecessary**: the 4060 remains the instrument of record, so the published
  numbers are not being restated on new hardware.

**→ Bar C — node equivalence. This is the bar.**

> The same input, sent to both nodes, produces the **same IMB1 record and the same SB2
> verdict**.

Concretely, pre-register before running anything:

| Check | Bar |
|---|---|
| Sidecar offline suite on the Mac | 24/24 pass |
| `/health` on the Mac | `imb1_ok`, `sb2_ok`, `bb3_ok` true; **7,055** appearance / **11,609** profile rows; `ollama_up` true. `torch_cuda_available: false` is expected, not a failure |
| **Imprint reads** — N pill photos through both nodes | I1 and I3 strings **identical** per photo. This is the channel most likely to diverge and the one that drives 83.9% of non-verifications |
| **Colour / shape / type** | identical `colour_modes`, `shape_out`, `type_out` per photo |
| **SB2 verdict** — same record + same profile DINs | **zero** verdict flips (verify/reject/abstain) across nodes |
| **BB3** — N questions through both nodes | same resolved DIN set and same cited sources |
| Latency | recorded, not bounded — §5's B5 gap is a deliverable, not a pass/fail |

Use a shared, fixed photo set for both nodes so the comparison is paired. The existing
`data/eval/` artefacts (`Pill1.jpg`, `Pill2.jpg`, `prescription1.jpg`) are the obvious
starting point; the 186-photo OTC set is available if a larger N is wanted.

**If equivalence fails**, that is a real finding, not a port failure — and the fallback
is well-defined: keep the Mac in the pool for **Q&A and prescription OCR only**, and pin
pill analysis to the 4060. Say so explicitly rather than shipping a node that silently
disagrees.

Counts, not percentages, at small n.

---

## 11. Open questions for Muthu

1. ~~Replacement or second node?~~ **Answered 2026-08-13: second node.**
2. **List order in `BRAINS_SERVICE_URLS`** — which node is primary? The 4060 first
   preserves today's behaviour and makes the Mac pure failover; the Mac first makes the
   Mac the default instrument, which contradicts "4060 is the instrument of record"
   unless the pin is used.
3. **Who owns the BB3 copy** once there are two, and does the Mac get the store by
   physical copy or by rebuilding it from `export_store.py`? Related: what is the
   procedure that keeps them from drifting (§9, consequence 2)?
4. **Is a persisted pin wanted?** The current pin is process-local and dies on restart
   (`brains_registry.py:36-37`), so it cannot be relied on to hold a measurement run
   across a redeploy.

---

## Appendix — file reference

| Path | What |
|---|---|
| `PillSafe/dev/brains/app.py` | the sidecar service; endpoints, subprocess spawns, `/health` |
| `PillSafe/dev/brains/requirements.txt` | the pinned stack — the thing being ported |
| `PillSafe/dev/brains/README.md` | install order, endpoint behaviour, test suite |
| `PillSafe/dev/brains/rx_extract.py` | Rx proposer, Ollama config |
| `PillSafe/dev/brains/rx_ocr_sub.py` | prescription OCR subprocess |
| `PillSafe/dev/brains/qa.py` | BB3 Q&A context mode |
| `IMB1_v0/imb1/pipeline.py` | FastSAM + S2 + colour; device selection at :79 |
| `IMB1_v0/imb1/ocr_sub.py` | dual-read imprint OCR subprocess |
| `IMB1_v0/README.md` §"GPU vs CPU" | the only latency record that exists |
| `IMB1_v0/CONTRACT.md` | capture assumptions, the two-process constraint |
| `SB2/CONTRACT.md` | matcher semantics, frozen operating point |
| `SB2/sb2/matcher.py:152` | the knife-edge note — why small OCR deltas flip verdicts |
| `PillSafe/dev/backend/app/services/brains_registry.py` | **the pool** — selection rules, health cache, pin |
| `PillSafe/dev/backend/app/core/config.py:78-87` | `BRAINS_SERVICE_URL` + `BRAINS_SERVICE_URLS` |
| `PillSafe/dev/backend/app/api/v1/routes/admin.py:134-158` | pool status + pin endpoints |
| `PillSafe/dev/backend/app/api/v1/routes/pill.py:120-125` | per-request URL resolution (pill path) |
| `PillSafe/dev/backend/app/api/v1/routes/qa.py:78-82` | per-request URL resolution (Q&A path) |
| `BB3/bb3/store.py` | SQLite + memmap access layer |
| `BB3/bb3/retrieve.py` | embedder + candidate gather (:243-250) |
| `BB3/CONTRACT.md` | local-only rule, Ollama requirement |
| `ops/start_sidecar.cmd` | launch command, tailnet binding |
| `documentation/deployment/DEPLOY_GUIDE.md` §12 | sidecar restart = the brain-deploy mechanism |

---

*Compiled 2026-08-13 by reading the code and filesystem directly. No decision recorded
in the project ADR — this brief is input to that decision, not a record of one.*
