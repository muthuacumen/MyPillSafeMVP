# Multi-Pill (Tray) Support — Effort Scoping for the Capstone Presentation

**Type:** Read-only scoping report. No code was changed or executed to produce this document — every
claim below is either a direct read of current source (cited by file:line, read live during this
session) or a cross-check against `Futureworks.md` entry 23 (and adjacent entries 24/25), which a
prior session already filed on this exact question.

**Context this report was written under:** a separate, concurrent `/pillsafe` session was actively
running the production deployment (M1 sprint) while this report was produced. Nothing here reads as
"do this tonight against production" — the explicit ask was for the leanest path that does **not**
compete for GPU/RAM/CPU with that session and does **not** touch anything the deploy session might be
mid-edit on.

---

## 1. Bottom line

- **Full multi-pill support, wired end-to-end through the app** (tray photo → N pill IDs → rendered
  in the UI) is already scoped by this project's own paperwork as roughly **one week of build-and-
  test**, filed as **Futureworks #23**, ruled **MVP-critical** by Muthu, but explicitly **not
  measured** — it's a judgment call, not a timed estimate. **This is not achievable by tomorrow.**
- **The segmentation problem — "find the N pills on a known tray" — is already solved.**
  `nb08_wells.py` (prototype tree) does per-well occupancy against the known 6-well ArUco card, is
  tested, and is frozen. It has simply never been wired into the app.
- **The leanest thing that gets a real multi-pill demo moment for tomorrow** is a small, additive,
  prototype-only script that composes two already-working pieces — well occupancy + the existing
  single-pill reader, looped per well — run once offline on already-captured tray images. This is
  hours of work, touches zero production/sidecar/frontend code, and (if the currently-deployed
  PaddleOCR reader is used, not the new two-stage VLM reader) creates **no GPU contention** with the
  concurrent deploy session.
- This does **not** close Futureworks #23. It gets a demo artifact, not a shipped capability.

---

## 2. What was verified live, right now (not recalled from memory)

| Claim | Verified by | Result |
|---|---|---|
| Production `analyze_pill()` is one-photo-in, one-record-out | Read `IMB1_v0/imb1/__init__.py:96` directly | Confirmed: `def analyze_pill(photo_path: str \| Path, calib_mode: str = "C-A") -> dict` — single record, `{"detected": False}` on nothing found |
| `/pill/analyze` is a single-image endpoint | Read `PillSafe/dev/brains/app.py:324` directly | Confirmed: `UploadFile = File(...)` (singular), returns `{"record": record, "match": match}` — one of each |
| Per-well occupancy already exists and is tested | Read `IMB1_Prototype/NB08_Notebook/src/nb08_wells.py` in full | Confirmed: `occupancy()` returns a per-well `{occupied, inst, mask, ...}` list against the known 6-well card geometry, frozen thresholds, documented design-set separation |
| Frontend result rendering is a modest, single-purpose component | Located `AnalyzePage.tsx` (266 lines) and `PillResultPanel.tsx` (262 lines) | Sized consistently with "loop it," not "rewrite it" — not independently timed |

Nothing in the code has moved since Futureworks #23 was filed. The estimate below is not stale.

---

## 3. What already works: `nb08_wells.py`

This module answers a different, narrower question than "find any pill anywhere in a photo." Instead
of picking one global winner, it asks **six independent yes/no questions** — "is well *k* occupied?"
— against a known card geometry (ArUco-registered homography, six dimple centres). Three prior
general-purpose pickers were measured and killed on this exact problem (frozen 0/36, geom 7/36,
bright 12/36 against a required ≥22/24 bar); the per-well reformulation is what actually passed.
Mechanically:

- Candidate blobs are filtered by area/aspect/border touches (same frozen filters as the single-pill
  path), then tested per well: **containment** (how much of the blob sits inside this one cell) must
  be ≥0.80, and **fill** (how much of the cell the blob covers) must be ≤0.45 — a pill fills roughly
  31% of its cell; an empty floor fills 85–100%. A blob spanning two wells fails containment in
  *both* and is rejected everywhere, by construction, not by a tuned threshold.
- A same-cell tie-break (brightness relative to the cell's own floor) resolves the rare case of two
  survivors in one well.
- Documented, stated-in-advance limitation: a large dark pill (DIN 02306409) is missed 2/2 because it
  isn't photometrically separable from an empty well on this build — a real, named gap, not a hidden
  one.

This is the hard 80% of "multi-pill capture" and it's done. What's missing is entirely the wiring
around it.

---

## 4. The full-integration scope (Futureworks #23) — why it's ~1 week, not a day

Futureworks #23 states the ask as five items to carry the existing single-pill contract to 1→N:

1. **`analyze_tray()`** in `IMB1_v0` — a new entry point wrapping `nb08_wells.py`'s occupancy + crop,
   then running the existing single-pill pipeline per occupied well. *Cheap* — the hard part
   (segmentation) already exists.
2. **The IMB1→SB2 contract going 1→N** — today a single dict, a tray call needs a list of records,
   each independently matched against the patient's profile. *This is the real work* — it's a change
   to safety-critical matcher semantics, not plumbing, and this project's own discipline (bars,
   mutation testing, adversarial refutation passes on every change of this shape) applies here too.
3. **The sidecar** (`PillSafe/dev/brains/app.py`) returning a list from a new/extended endpoint
   instead of the current single `{record, match}` shape. Plumbing.
4. **The frontend rendering N results** in one screen instead of one. Plumbing, sized moderately by
   the existing component's line count, but untimed.
5. **N sequential reader passes under the model-lifecycle arbiter's one-model-resident-at-a-time GPU
   constraint** (`nb08_arbiter.py`, measured 8.00 GiB VRAM ceiling on the target machine — any two of
   the project's three local models exceed the card). N wells means N model loads/swaps *in
   sequence*, not in parallel. This is a real latency cost baked into the hardware, not a wiring
   afterthought — **but it only applies if the tray path uses the new two-stage (A3+A4c) reader.**
   The currently-*deployed* reader (PaddleOCR, via a plain subprocess call) is not managed by the
   arbiter at all and carries none of this cost (see §6).

Futureworks #23 itself is explicit that **the ~1 week figure is Muthu's judgment call, not a measured
engineering estimate** — no task-level build was scoped or timed. This report does not tighten that
estimate; it confirms the estimate's inputs (items 1–5) are still accurate against current code, and
separates which item actually drives the timeline (item 2, with item 5 as a real but reader-dependent
tax).

---

## 5. Measured evidence: what happens if you just point the current app at a tray today

This was directly measured, not predicted, in the M1-sprint DEMOPREP session
(`archive/demoprep/02a_tray_probe.md`, raw data in `02_tray_probe_raw.json`). Eight full 6-well tray
frames (Sample17) were pushed through the *current, unmodified* `analyze_pill()` → `sb2.match_pill()`
path, exactly as a user would hit it today:

| Result | Count | Detail |
|---|---|---|
| `detected: true` | **8/8** | A tray photo does **not** fail cleanly — FastSAM always finds *something* |
| Incidentally correct verify | **2/8** | S09P2 → benadryl, S10P3 → asa.81 — both genuinely in-scene |
| Abstain/reject | 6/8 | — |
| Wrong-drug false-accept | **0/8** | — |

The bounding boxes are the tell: every one is a small fraction of a several-thousand-pixel-wide
frame (300–1200 px on a side) — the single-pill segmenter is isolating one arbitrary region out of a
six-pill scene, not "the pill the user meant." The two correct hits are consistent with lucky scene
composition, not a designed selection mechanism — the same conclusion `nb08_wells.py`'s own
docstring already reached about general (non-well-aware) multi-pill pickers.

**Why this matters for tonight:** it confirms, on the exact current production code, that "just
photograph the tray with what we have" is not a viable shortcut — it's not that it fails safely, it's
that it succeeds *unpredictably*, which is worse for a scripted, repeatable demo. This is also why the
prior session's own ruling was: tray images are **out** as a demo entry point on the current code, and
the demo instead proceeds on single-pill capture-card images
(`data/nb08_images/OTC_Images/Raw/`, `calib_mode="C-A"`).

That ruling is about presenting the *current app* live. It does not preclude building the small,
isolated, non-production `analyze_tray()` composition proposed below and demoing *its* output
separately.

---

## 6. GPU/resource contention analysis (the binding constraint for tonight)

Two readers exist in this project and they are **not equally expensive**:

- **The currently-deployed reader** (`_run_ocr_subprocess`, PaddleOCR via `subprocess.run`) is what
  production `analyze_pill()` actually calls today. It is a plain child-process call, not managed by
  the model-lifecycle arbiter, and does not participate in the one-model-resident-at-a-time GPU
  contract.
- **The new two-stage reader** (A3 + A4c, Ollama + transformers) is the one bound by the arbiter's
  8.00 GiB VRAM ceiling and the one-resident-at-a-time rule — and it is also the one the concurrent
  deploy session is actively exercising tonight (model loads/swaps are part of what "deploying M1"
  means).

**Recommendation, stated plainly: build and run the demo-only `analyze_tray()` composition against
the currently-deployed PaddleOCR reader, not the new two-stage reader.** This keeps the demo entirely
off the GPU-arbiter's contended resource, avoids any risk of the demo's inference stealing VRAM from
a model the deploy session has resident, and avoids any risk of the demo *triggering* a model swap
that could interrupt the deploy session's own state. Any inference run should still be a short,
isolated burst, not sustained concurrent load.

---

## 7. A closed risk worth naming (de-risks reusing the current reader)

Futureworks #25 documented a real, reproducible production bug in exactly the function this
report proposes reusing per well: `_run_ocr_subprocess` (and the child `ocr_sub.py`) crashed with
`UnicodeEncodeError` on non-ASCII PaddleOCR output (cp1252 console encoding), hard-failing the whole
scan (HTTP 422) on 4 of 52 real single-pill photos during this same DEMOPREP session. **This is
CLOSED as of 2026-08-13** — both legs (child `sys.stdout`/`stderr` reconfigured to UTF-8, parent
subprocess call given explicit `encoding="utf-8", errors="replace"`) are fixed and mutation-tested.
Worth stating because it means the lean path's core building block — call `analyze_pill()` per
cropped well — is calling into code that was, until very recently, known to crash on a meaningful
slice of real images. It no longer does. This was verified by reading the current (fixed) source and
the Futureworks entry's closure note, not assumed.

---

## 8. Recommended leanest path for tomorrow

**Scope:** a new, additive, prototype-only module (e.g.
`IMB1_Prototype/NB08_Notebook/src/nb08_tray_demo.py`), never touching `IMB1_v0`, the sidecar, the
SB2 contract, or the frontend. It:

1. Loads a tray photo and the known card homography (already available — `nb08_wells.py` depends on
   it, `IMB1_v0`'s own calibration already produces it for the single-pill path).
2. Calls `nb08_wells.occupancy()` to get the occupied wells.
3. Crops each occupied well and runs the *existing* single-pill pipeline (the currently-deployed
   PaddleOCR-based `analyze_pill()` internals, or the equivalent torch-stage + OCR call) on each crop
   independently.
4. Collects the N results into a list and prints/renders them — a notebook cell or a small script
   output, not an app screen.

**Why this is genuinely small:** every piece it calls already exists and is already tested in
isolation — well occupancy (§3) and single-pill reading (production code, §2/§7). The only new code
is the loop and the crop-extraction glue between them. This is composition, not new engineering — a
few hours, not the ~1 week of Futureworks #23, because it deliberately skips the three items that
make #23 expensive: the SB2 contract going 1→N (§4 item 2), the sidecar API change (item 3), and the
frontend change (item 4). Those three are exactly what "app entry point" (Futureworks' actual ask)
requires and this demo-only path does not.

**What it buys:** a real "one photo, N pill identifications back" moment to show tomorrow — either
live (if the GPU is free of the deploy session's load at demo time) or as a captured screenshot/log
from a run done ahead of time on the already-available Sample17 tray images or the demoprep OTC
imagery, laid out on the physical card.

**What it explicitly does not buy:** app/UI multi-pill support, a promotable change, or closure of
Futureworks #23. The next session after the presentation should treat #23 as still fully open, at its
filed ~1 week estimate, gated on Muthu's approval per its own "THE ASK" framing.

---

## 9. Guardrails for tonight (do not cross these)

- **Do not edit `IMB1_v0`, `PillSafe/dev/brains/app.py`, the SB2 matcher, or any frontend file.**
  Those are the concurrent deploy session's surface and/or the ~1 week item, not tonight's scope.
- **Do not run the new two-stage (Ollama/transformers) reader** as part of this demo build — use the
  currently-deployed PaddleOCR path to avoid GPU-arbiter contention (§6).
- **Run inference in short, isolated bursts**, not sustained load, and prefer running against
  already-captured images over live capture if the deploy session is mid-run.
- **Do not present this as "multi-pill is supported"** — it is a research-instrument demo of a
  composition of two already-working pieces, explicitly not wired into the product.

---

## 10. Open decisions (Muthu's, not this report's to make)

- Whether to actually build the tonight-scoped demo script, or rely on the existing single-pill demo
  path (already the M1-sprint's own fallback ruling, §5) and present Path A conceptually via this
  document + `nb08_wells.py`'s own measured numbers instead of a live/recorded run.
- Whether Futureworks #23's full ~1 week build gets approved as a post-presentation, post-deploy
  session — this report does not change that ask, only re-confirms its inputs are current.

---

## 11. Deployment sequence broken down bottom-up — is the ~1-week estimate justified?

This section re-derives Futureworks #23's five items from the actual code (not from the entry's
prose) and asks, item by item, whether the effort implied is smaller, larger, or about the same as
"~1 week." It also names one real requirement Futureworks #23 does not mention at all. Everything
below is grounded in source read live this session: `nb08_arbiter.py`, `nb08_imb1.py`,
`nb08_record.py` (the C6 contract), `sb2/__init__.py::match_pill`, `AnalyzePage.tsx`, and
`PillResultPanel.tsx`.

### 11.1 Step-by-step breakdown

**Phase A — `analyze_tray()` (Futureworks item 1)**

| Step | What it needs | Status |
|---|---|---|
| A1 | Per-well occupancy + crop extraction | **Done** — `nb08_wells.occupancy()` |
| A2 | Per-crop single-pill read (appearance + imprint) | **Done** — reuses `analyze_pill()` (deployed) or `_run_appearance_heads()` + a reader (prototype C7 path) |
| A3 | Loop A1→A2 across occupied wells, collect a list | New, but pure composition of two tested pieces |
| A4 | Pre-registered bars for the new loop (this project's standing discipline — nothing ships without them) | New |

A3 is genuinely small. A4 is not optional in this project's own working method (every prior
C-phase item shipped with 10–28 bars, mutation-tested) — it's real time, but it's process overhead
on a small diff, not engineering difficulty.

**Phase B — the IMB1→SB2 contract going 1→N (item 2)**

This is the item Futureworks calls "the real work," and reading the actual C6 contract
(`nb08_record.py`) both confirms and re-shapes that claim:

- **Good news, found by reading the contract, not assumed:** `PillRecord` is already fully
  self-contained per photographed pill — it carries its own `lexicon_profile_dins` and is validated
  independently. `sb2.match_pill(record, profile_dins)` (`SB2_Prototype/sb2/__init__.py:81`) already
  takes exactly **one** record and returns exactly one decision. **Nothing in the contract or the
  matcher needs to change shape for N wells** — a tray result can legitimately be "call
  `analyze_pill(crop_i, profile_dins=...)` then `match_pill(record_i, profile_dins)`, N times, same
  profile list every time, collect N decisions." No new schema, no new matcher logic.
- **So why is this still real work?** Two reasons Futureworks doesn't spell out:
  1. **The C7 two-list guard** (`assert_same_profile`) exists specifically because a mismatched
     profile between the reader and the matcher fails *silently* (an unexplained abstain). Looping
     N times means asserting this guard holds independently for all N calls, not just proving it
     once — a real but small addition to the bar set.
  2. **Partial-failure isolation is a genuinely new requirement Futureworks #23 never names.**
     Today, `/pill/analyze` raises `HTTPException(422, PILL_ANALYSIS_FAILED)` on *any* exception
     from `analyze_pill()` (`app.py:356-362`, read directly) — the whole request dies. For a
     6-well tray, one well's OCR failure must not discard the other five successful reads. This
     needs new isolation logic (catch-per-well, degrade gracefully, report which well failed and
     why) that does not exist anywhere in the current single-pill contract, and it touches the same
     "fail loudly, never silently" discipline this project applies everywhere else in the record
     contract — so it needs its own bars, not a quick try/except.

Net: Phase B's *coding* surface is smaller than Futureworks implies (the contract itself doesn't
need surgery), but it carries a real, previously-unnamed sub-requirement (partial-failure isolation)
that offsets that savings.

**Phase C — the sidecar endpoint (item 3)**

Reading `app.py:324-380` (the current handler) shows the existing pattern is already reasonably
close to what a tray handler needs: parse `profile_dins`, call the pipeline, call the matcher,
return JSON. Extending it to accept N crops (or one tray photo it self-segments) and return a list
is structurally the same shape repeated, **plus** the partial-failure handling from Phase B. Genuinely
plumbing, on top of whatever Phase B produces — not an independent cost driver.

**Phase D — frontend rendering N results (item 4)**

Futureworks called this "plumbing." Reading `AnalyzePage.tsx` and `PillResultPanel.tsx` in full
shows it's smaller than a rewrite but larger than pure plumbing, for three concrete reasons:

1. **`PillResultPanel` is already self-contained** (its `selectedDin` state is local, not lifted) —
   rendering N of them in a list (`results.map(r => <PillResultPanel result={r} .../>)`) is
   mechanically straightforward. This part really is close to "loop it."
2. **Voice narration is written for exactly one outcome** (`AnalyzePage.tsx:150-163` branches on a
   single `data.match.decision`) — this app's population (seniors, language barriers) leans on voice
   as a first-class channel, not a nice-to-have, so "read out 6 independent verify/reject/abstain
   outcomes intelligibly" is a real content/UX decision (sequential? summarized first, detail on
   request?), not a data-shape change.
3. **The in-flight progress messaging is explicitly tuned for one slow call**
   (`AnalyzePage.tsx:62-64`, comment: *"the first sidecar call per process is slow... commonly
   30s+"*). A tray means up to N such calls in one request (see Phase E) — the current
   cycling-message spinner pattern was not designed for that and reads as broken/stuck without a
   per-well progress indicator.
4. **"Retake" is a single, whole-photo action today.** For a tray, does retake mean the whole card or
   just one well's crop? That's a product decision with UI consequences, not implied by the current
   code.

Item 4 is real, scoped work — closer to the better part of a day for a bare stacked-card version, more
if the progress/voice/retake decisions get proper design attention rather than a placeholder.

**Phase E — N sequential model loads under the GPU arbiter (item 5)**

Reading `nb08_arbiter.py` in full confirms this is the item with the least certainty, and quantifies
why. Two facts combine:

- `ModelArbiter.acquire()` holds a single reentrant lock for the **entire** inference body and
  evicts whatever is currently resident before loading the requested model — by design
  ("Latency is explicitly NOT a constraint... visible swap cost is a wanted infrastructure talking
  point. Do not re-optimise this into a cache," per the module's own docstring).
- The two-stage reader's own shape already does **up to two acquisitions per single pill** — Stage 1
  (A3, Ollama) always, Stage 2 (A4c, transformers) conditionally when Stage 1 says `TEXT`. Each
  acquisition after a *different* model was resident is a swap: evict, verify release (polled,
  budgeted up to `ps_settle_s`, 30s for Ollama), then load.

**Multiplied across a 6-well tray, this is structurally up to 12 sequential model swaps in one HTTP
request**, if the tray path uses the new two-stage reader per well. No number in the codebase states
an absolute swap duration — the closest grounded figure is the frontend's own comment that a single
first sidecar call already runs **"commonly 30s+."** Twelve swaps at that order of magnitude is
minutes, not seconds, for one tray photo. This is not a defect — Muthu's own standing instruction is
that visible swap cost is a *wanted* talking point, not a bug — but it is a UX design question this
project has not yet had to answer for a chained, N-deep sequence inside one synchronous request, and
"return a blocking HTTP response after several minutes" is a different problem than the frontend's
current single-call spinner solves.

**The escape hatch, unchanged from the read-only scoping pass:** none of this GPU-arbiter cost
applies if the tray path uses the *currently-deployed* PaddleOCR reader (a plain subprocess, not
arbiter-managed) instead of the new two-stage reader. That reader is less capable (it's the one
`§3.12`/`§3.15` of `NB08_Identification.md` measured fabricating on blank faces, per prior findings)
but it removes Phase E's cost and uncertainty almost entirely. **Which reader the shipped tray
feature uses is a real fork in the design, not a detail** — and Futureworks #23 does not name it as
a decision point.

### 11.2 A cross-cutting cost neither list separates out: this project's own discipline

Every comparable contract-layer change in this project's history (the C.1–C.7 sequence: the C6
record, the model arbiter, the C7 profile-into-IMB1 change, the A4c lexicon builder, the allowlist,
the UI messages, the deployed reader) shipped with 10–28 pre-registered, mutation-tested bars, and
several were caught by adversarial refutation passes that found real defects the build itself
missed. That discipline is not overhead to be trimmed for a demo build — it is the reason this
project has caught its own safety defects before they shipped, repeatedly. Any estimate for Phase B
in particular should assume bar-writing and at least one adversarial-refutation pass, not just the
code.

### 11.3 Verdict: is ~1 week justified?

**Yes, roughly — but not for the reason Futureworks #23 states, and the risk is concentrated
differently than its five-item list suggests.**

- Phase A (segmentation → tray loop) and Phase C (sidecar plumbing) are genuinely small — well under
  a day of raw coding each, though A also owes its own bar set.
- Phase B's *coding* surface is smaller than advertised (the contract and matcher already generalize
  to N calls without modification), but it owes a real, previously-unnamed requirement
  (partial-failure isolation) plus this project's standing bar/mutation-test/adversarial-audit
  discipline (§11.2) — call it one to two days once that overhead is counted honestly, not the
  "biggest item" framing Futureworks gives it in isolation.
- Phase D (frontend) is a half-day-to-a-day for a bare version, more if the voice-narration and
  progress-messaging questions get real design attention rather than a placeholder — this project has
  no comparable frontend sprint precedent to calibrate against, unlike the backend/contract work.
- **Phase E is the genuine unknown**, and it cuts both ways depending on a decision Futureworks never
  poses explicitly: ship the tray feature on the *new* two-stage reader (up to 12 sequential model
  swaps per tray request, an unmeasured latency floor, and likely a UX redesign away from a blocking
  request toward some kind of progressive/async response) — or ship it on the *currently-deployed*
  reader (near-zero additional cost, but the weaker, already-measured-to-fabricate reader).

Summed at face value (A+B+C+D, excluding E's redesign risk), the total lands comfortably inside a
week, arguably closer to 3–4 focused days if worked with the same intensity the C.1–C.7 sprint
showed (seven comparable contract-layer modules landed in a single day of that sprint — a different
operating mode than ordinary week-long work, so it's a data point on achievable pace, not a
promise). **What actually justifies keeping the estimate at "~1 week" rather than tightening it is
Phase E**: if the answer is "ship it on the new reader," the sequential-swap latency is unmeasured
territory that could force a genuine UX redesign (async job + poll, rather than one blocking call),
which is exactly the kind of unbounded item that inflates a scoped estimate. If the answer is "ship
it on the currently-deployed reader for now," the honest bottom-up total is *tighter* than a week,
and the estimate should say so explicitly rather than carry Phase E's worst case by default.

**Recommendation for whoever approves this work:** decide the Phase E reader question *before*
scoping the build, not during it. That single decision moves the estimate more than any other item
on this list.

---

## 12. A candidate simplification for Phase E: could A4c's own 4.4B model replace A3?

This section is research, not a build — nothing below has been run. It follows directly from §11.1
Phase E, where the GPU arbiter's one-model-resident-at-a-time constraint was identified as the
genuine unknown in the multi-pill timeline (up to 12 sequential model swaps for a 6-well tray if the
tray path uses the two-stage A3+A4c reader). This asks whether that cost can be designed away rather
than absorbed.

### 12.1 The question

A3 (Stage 1, presence gate) and A4c (Stage 2, constrained read) are two different model *sizes* on
two different *runtimes* today. If the same model that already runs A4c could also do A3's job, the
tray-reading pipeline would need **one** resident model instead of two — eliminating the swap chain
Phase E flagged, not just budgeting for it.

### 12.2 What's confirmed from the project's own source, read directly this session

- **A3's model is already quantized**, exactly as suspected. Ollama's own `/api/tags` metadata,
  captured live in `results/vlm_imprint_read/_a3_env_provenance.json` during the original run:
  `"parameter_size": "8.8B", "quantization_level": "Q4_K_M", "format": "gguf"`, ~5.72 GiB resident.
- **A4c's model is `Qwen/Qwen3-VL-4B-Instruct`, 4.44B params, 4-bit NF4** — confirmed from
  `nb08_constrained_score.py:91,164-165`, whose own comment states why: *"bf16 weights are 8.88 GB
  for 4.44B params; this GPU has 8.6 GB total. Full precision does not fit, so 4-bit is not a
  preference."* This is the exact model the user asked about.
- **Why they're split across runtimes today is an API constraint, not an accuracy argument**:
  `NB08_C6_Contract_Build.md:61` — *"Ollama exposes no logprobs, and A4c's PMI margin IS the safety
  mechanism."* A4c teacher-forces a closed lexicon and scores candidates by log-likelihood margin,
  which needs per-token logprobs Ollama's API doesn't return.
- **A4c already has a working "no imprint" detector, at no extra model call.** The constrained
  scorer's ballot includes a `NULL_LABEL = "__NONE_OF_THESE__"` entry, and the original prereg
  measured it directly: **Bar B3, §3.15.1 — 14/14 correct on blank faces**, NULL precision 14/15.
- **What A4c cannot do is the reason Stage 1 survives**: its margin collapses "genuinely no imprint"
  (terminal) and "an imprint present but unresolvable" (recoverable — reshoot/flip) into the same
  low-margin outcome. v3 §1.8 routes those to opposite user actions, and H3 (§3.16) found this
  three-way distinction is what earns Stage 1 its place — not raw reading capability.
- **The 4.4B model has never been run in free generation inside this project** — only in constrained,
  teacher-forced scoring mode, from its first appearance (§3.15.1). The only internal measurement of
  a local Qwen3-VL model doing free-generation reading belongs to the 8.8B model.
- **The call is a portable HTTP/prompt call, not Ollama-specific**: `nb08_read16_vlm.py::call_a3` is
  a plain POST to `/api/generate` with a self-contained prompt string (reproduced verbatim in that
  file, "sent verbatim... changing a word would measure the prompt rather than the reader").
- **`ConstrainedScorer.score_crop()` is generic over its `lexicon` argument, read directly this
  session (`nb08_constrained_score.py:256-282`)** — it is not hardcoded to drug names. It teacher-
  forces *any* `{label: surface_string}` dict against the crop and returns a PMI margin among
  whatever candidates it's given. This is the seam §12.5 below builds on: a presence classification
  is just a different lexicon through the same, already-built, already-partially-validated function
  — not a new model call.

### 12.3 External corroboration (searched today, outside the project)

Qwen's own published benchmarks show the 8B variant meaningfully outperforming the 4B variant on
OCR-specific evaluations (CC-OCR, OCRBench, OCRBench-V2), and the gap widens on **degraded images
specifically: 87–91% (8B) vs 82% (4B)** — the exact regime this project has repeatedly found to be
the bottleneck (low-contrast deboss, motion blur, flash-lit crops). This is real evidence against
assuming parity, not just a generic "smaller model is somewhat worse" caveat. (The published
comparison used the "Thinking" variants; this project's deployed models are both "Instruct" —
directionally informative, not a precise match.)

### 12.4 The notebook where A3 (8.8B) was proved effective — found, and what it actually measured

**`notebooks/NB08_05_A3_Qwen3VL.ipynb`**, executing **`specs/NB08_VLM_ImprintRead_Prereg.md`**
(filed 2026-08-08, *before any model saw a crop* — status at filing: "set built, bars fixed, zero
reads taken"). Its companion, running the baseline arm of the *same* 3-arm test, is
`notebooks/NB08_04_A1_PaddleOCR.ipynb`. Results are folded into `specs/NB08_Identification.md`
§3.12. Precisely what it measured, since any new experiment on the 4.4B model should mirror it:

| | detail |
|---|---|
| **Set** | 100 crops from `IMB1_Prototype/review/nb04_true_imprint/` (311 Muthu-verified per-face true imprints, Pillbox **studio** imagery, blind-read discipline) |
| **Strata** | 91 legible verified faces (capability) + **7 confirmed NO-IMPRINT faces** (fabrication traps) + 2 excluded |
| **Bar 4.1 (primary, capability)** | exact match vs A1 (PaddleOCR) on the 91 legible faces, using the project's existing `matcher.tokens()` normaliser |
| **Bar 4.2 (safety-primary, can fail an arm outright)** | **0 fabrications** — any non-empty read on the 7 confirmed-blank faces is a fabrication; abstention is a PASS, not a miss |
| **Bar 4.3 (secondary)** | prior-driven completion — a read matching the *other* face's imprint rather than the photographed one, reported not barred |
| **Result (§3.12)** | A3 (8.8B) is the **only** arm to clear both bars: 49/91 exact (53.8%), **0/7 fabrications**, 7/7 blanks correctly returned NONE |
| **Threat, stated at filing** | "Pillbox is STUDIO imagery; our capture is a flash-lit tray... **a pass here does NOT license deployment** — it licenses the next test, on our own crops." |

That last line matters: the 8.8B model's clean pass has **never itself been re-run on this
project's own flash-lit tray imagery in free-generation mode** — Sample16/17 tested the *constrained,
scored* A4c pipeline on real crops, not bare A3-style free generation. So the proposed step below
closes two gaps at once, not one.

### 12.5 A better design: score a presence ballot instead of generating freely

The free-generation arm (§12.2/12.3 above) works, but it reintroduces exactly the fabrication mode
this project moved A4c *away from* — and does it on the smaller, externally-weaker-on-degraded-images
model. There is a cleaner design, found by reading `score_crop()` itself rather than assumed:

**Replace "call A3, get a free-text string, bucket it into TEXT/UNREADABLE/NONE" with "score a
3-entry presence ballot the same way A4c already scores its drug ballot."** Concretely: call
`ConstrainedScorer.score_crop(crop_path, {"legible": "...", "illegible": "...", "blank": "no
imprint is visible on this face"})` and take whichever candidate wins the PMI margin — no
free-text generation, no separate model, no separate runtime.

**Why this removes the swap structurally, not just as a matter of scheduling.** Traced directly in
`nb08_reader.py`: Stage 1 and Stage 2 today acquire two *different* names from the arbiter
(`self._arbiter.acquire(self._a3_model)`, then `self._arbiter.acquire(self._a4c_model)`), and
`ModelArbiter.acquire()` evicts whatever is resident before loading a different name. Its own fast
path (`nb08_arbiter.py:543-545`): *if the requested name is already resident and loaded, yield and
return* — no eviction, no load. If presence-scoring and drug-scoring both acquire the **same**
name (because they're now the same model), the second call in every face is a no-op. Across a
6-well tray, this is the difference between up to 12 sequential swaps (§11.1 Phase E) and **zero**
— the imprint pipeline never touches a second model at all. It's also plausibly faster per call on
its own terms: a handful of short teacher-forced forward passes, not the autoregressive generation
that makes today's A3 call run 17.2s median (§3.12).

**What's already true in this project's own favor:** the drug-ballot's `NULL_LABEL` entry is scored
by this exact mechanism today and was measured at **14/14 correct on blank faces** (Bar B3,
§3.15.1) — so "blank vs not" is not a new question for this scoring approach, only "blank vs
illegible-but-present" is. That narrower, genuinely open question is what H3 (§3.16) found the
*existing drug-name ballot* structurally cannot answer — a different ballot, built for this
question specifically, was never tested against it.

**What's unproven, stated plainly:** the exact wording of the three candidate surfaces needs real
design care (the same kind that went into choosing `NULL_SURFACE`), and whether a 3-way presence
ballot actually separates "illegible mark present" from "genuinely blank" with a clean margin has
never been measured — that is precisely what Step 1 below tests.

### 12.6 Proposed Step 1: score both A3 designs, same protocol, on the `WIP/Set2` reserve set

**Set:** `IMB1_Prototype/NB08_Notebook/data/nb08_images/Tray_Images/WIP/Set2` — 52 full tray photos,
shot 2026-08-05/06, read directly from its `shotlist.csv` this session. Found suitable for exactly
this purpose, for reasons the shotlist itself confirms:

- **It is unburned** — never scored, never used to fit or freeze anything (confirmed against every
  prior mention of this set in the project's own registers). A legitimate fresh reserve.
- **It already contains a ready-made fabrication-trap population**: frames `A01`–`A06` are
  **empty-tray controls**, shot specifically as an "FA denominator" — 6 frames × 6 wells = up to 36
  confirmed-blank well crops, once run through `nb08_wells.occupancy()` (already tested, §3 of this
  report). This is bar 4.2's exact population, on this project's own imagery instead of Pillbox
  studio imagery — the transfer test §3.12 itself called for and never got.
  - `G01`–`G04` (straddle / two-items-one-section) and `F01`–`F04` (oblique/handheld/shadowed/cropped
    frames) are already marked **"EXCLUDED FROM S1 AND S2"** / **"NOT SCORED"** in the shotlist
    itself — carry that exclusion into this experiment rather than re-deciding it.
- **Populated frames (`B`/`C`/`D`/`E` series) carry per-well product identity**, not blind per-face
  imprint text — e.g. `benylin|C`, `capsule1|IN`, `gravol|OUT`. This is enough to derive an
  *expected* imprint per well by joining against the reference workbook, but it is **not** the same
  rigor as Sample16's blind-adjudicated `true_imprint` — this project's own history (the Sample16
  face-truth defect, "modality was a property of the product and it is a property of the FACE") is a
  direct warning against silently treating product-level truth as face-level truth. **Bar 4.1
  (capability/exact-match) needs a truth-adjudication pass first — it is not ready to score today.**
  Bar 4.2 (fabrication on confirmed blanks) has no such dependency and can run first.
- **Product diversity is narrower than the full OTC-15** (benylin, capsule1, capsule2, gravol,
  senekot.s, dulcolax, allergy.remedy only) — a known, previously-documented limit of this set for
  DIN-breadth questions. Irrelevant to the blank/fabrication bar; relevant if bar 4.1 is later run.

**Proposed protocol, mirroring the original prereg's own discipline (bars filed before any read):**

1. Crop `A01`–`A06` into per-well images via `nb08_wells.occupancy()` — up to 36 confirmed-blank
   crops, zero new photography.
2. Score three arms against the same crops:
   - **Arm A3-8.8B (free generation)**: the current deployed `call_a3()`, unmodified, verbatim
     prompt, `qwen3-vl:latest` via Ollama — this also discharges the transfer test §3.12 flagged and
     never closed, independent of everything else being tested here.
   - **Arm A3-4.4B-generated**: the same free-generation prompt sent to the already-loaded
     `Qwen/Qwen3-VL-4B-Instruct` via `.generate()` — kept as a comparison point, but no longer the
     primary proposal (§12.5 explains why).
   - **Arm A3-4.4B-scored (primary)**: `ConstrainedScorer.score_crop()` against the new 3-entry
     presence ballot (legible / illegible / blank), on the same already-loaded 4.4B model — the
     design §12.5 proposes, scored for the first time.
3. **Bar, unchanged from §3.12's own safety-primary: 0 fabrications on the confirmed-blank set is
   non-negotiable for every arm.** For the scored arm, "fabrication" means the "blank" candidate
   fails to win the PMI margin on a confirmed-empty well — the direct analogue of Bar B3
   (§3.15.1, already 14/14 on the existing drug ballot's NULL entry) applied to the new ballot.
   Abstention/blank is a pass; anything else is a fail, regardless of how the other arms score.
4. Report exact fabrication counts, PMI margin distributions for the scored arm (does "blank" win
   clearly, or narrowly — the margin is the safety mechanism, not just the top pick), response
   latency for all three arms (the swap-elimination claim in §12.5 is architectural; the raw
   per-call latency comparison is still an open measurement), and — only after a truth-adjudication
   pass on the populated frames — capability as a secondary measurement, exactly as §3.12 kept
   capability secondary to the fabrication bar.

**What this buys:** a same-imagery, same-protocol, pre-registered answer to two questions at once —
whether the 4.4B model fabricates on this project's own tray captures, and whether a purpose-built
presence ballot can do what the existing drug ballot structurally cannot (§12.5) — using a set that
costs no new photography and was sitting unused for exactly this kind of purpose. **What it does not
buy:** a production decision by itself. Per this project's standing discipline (§11.2), any
promotion of a reader change still needs its own pre-registered bars, mutation testing, and an
adversarial refutation pass before it goes anywhere near the matcher.

---

**Owning docs referenced (not restated in detail above):**
`PillSafe/documentation/deployment/Futureworks.md` entries 23, 24 (dose-schedule, unrelated but
adjacent), 25 (OCR crash, closed) · `IMB1_Prototype/NB08_Notebook/src/nb08_wells.py` ·
`IMB1_v0/imb1/__init__.py` (`analyze_pill`, `_run_ocr_subprocess`) ·
`PillSafe/dev/brains/app.py` (`/pill/analyze`) ·
`archive/demoprep/02a_tray_probe.md` + `02_tray_probe_raw.json` (the 8-frame measurement) ·
`archive/demoprep/00_DEMO_STORY.md`, `DEMO_RUNBOOK.md` (current demo framing, single-pill entry
point) · `IMB1_Prototype/NB08_Notebook/src/nb08_arbiter.py` (GPU one-resident-at-a-time constraint,
read in full for §11) · `IMB1_Prototype/NB08_Notebook/src/nb08_imb1.py` (the C7 profile-aware
`analyze_pill`, read in full) · `IMB1_Prototype/NB08_Notebook/src/nb08_record.py` (the C6 contract,
`PillRecord`/`FaceRecord`/`assert_same_profile`, read in full) ·
`SB2_Prototype/sb2/__init__.py::match_pill` (per-record matcher signature) ·
`PillSafe/dev/frontend/src/pages/dashboard/AnalyzePage.tsx` and
`PillSafe/dev/frontend/src/components/PillResultPanel.tsx` (read in full for §11.1 Phase D) ·
`specs/NB08_VLM_ImprintRead_Prereg.md` (read in full, §12.4) ·
`specs/NB08_Identification.md` §3.12 and §3.15.1 (the A3-effectiveness result and A4c's NULL-detection
bar B3) · `src/nb08_read16_vlm.py` and `src/nb08_constrained_score.py` (read in full, §12.2/12.5/12.6)
· `src/nb08_arbiter.py` (the `acquire()` fast-path traced in §12.5) ·
`notebooks/NB08_05_A3_Qwen3VL.ipynb` + `notebooks/NB08_04_A1_PaddleOCR.ipynb` (located, §12.4) ·
`data/nb08_images/Tray_Images/WIP/Set2/shotlist.csv` (read in full, §12.6).
