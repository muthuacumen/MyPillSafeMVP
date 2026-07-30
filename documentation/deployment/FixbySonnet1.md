# FixbySonnet1 — Post-Deploy Fix Batch 1 (builder prompt)

**Authored by:** PillSafe SA (Fable session, 2026-07-27), from a full code review of every bug logged
during the Part B production deploy (`archive/docs/stepstakentodeploy.md`, ADR 2026-07-27 entries).
**Executor:** a Claude Sonnet builder session, working in `D:\Projects\PillSafe\PillSafe`.
**Verification afterwards:** Muthu tests on localhost, then a follow-up SA session independently
re-verifies (checklist in §9 — do not delete it).

---

## 0. Non-negotiables (read first)

1. **Commit nothing.** Work in the working tree on top of the current clean `main`
   (HEAD `115f8ba`). Muthu commits after his localhost pass.
2. **Touch only** `dev/backend/`, `dev/frontend/`, `.env.example`, `README.md`, and
   documentation files. **Do NOT touch** `dev/brains/` (sidecar), `docker/` compose files, or the
   frozen sibling packages `D:\Projects\PillSafe\{IMB1_v0,SB2,BB3}\` — nothing in this batch
   requires them, and they are contract-frozen.
3. **Decision-semantics freeze:** the `success`/`warning`/`danger` Tailwind decision tokens stay
   byte-identical; `PillResultPanel.tsx`'s decision rendering and its non-dismissible SafetyStrip
   stay intact (i18n key extraction of its copy is allowed — see Task 7 — but no semantic,
   colour, or structural changes to decision states).
4. **No fabricated stats/claims** anywhere in user-facing copy (binding repo rule).
5. **No droplet/production actions.** This is a local build. Redeploy (image rebuild/push, droplet
   pull) happens later per `DEPLOY_GUIDE.md` §4/§7 and is not your job.
6. **Honest reporting.** Run every verification bar in §8 yourself; never mark one green without
   running it. Append a `## Builder Report` section to the END of this file: exact test counts,
   deviations, anything you could not verify, and any new bug you find (finding bugs during
   mandated verification is the norm in this project, not a failure).
7. Backend venv: `dev\backend\venv` (py3.12). Frontend: `npm` in `dev\frontend`. Backend tests are
   hermetic (conftest forces `OCR_PIPELINE_ENABLED=false` + mocks sidecar calls) — currently
   **120 passed**; Task 5 deletes ~16 assistant tests and other tasks add new ones, so report the
   exact final count.

---

## 1. Context — what you are fixing

`https://mypillsafe.ca` went live 2026-07-27. E2E verification surfaced 4 app bugs (Bugs #1–#4
below) plus one anomaly. The SA has already root-caused most of them by code review; where a root
cause is stated below, it was verified by reading the code — build the stated fix rather than
re-deriving your own, and say so in your report if you disagree with a diagnosis.

Architecture reminders you need: OCR/pill/Q&A all call a **brains sidecar** over HTTP
(`app/services/brains_registry.py` resolves the URL). OCR failure must NEVER fabricate text — the
honest-503 path (`OCR_UNAVAILABLE`) shipped in Part A and must survive all your changes.
`_DEMO_RAW_TEXT` stays reachable only behind `OCR_PIPELINE_ENABLED=false`.

---

## 2. Task 1 — Bug #1: Rx-scan crash on real labels (clamp + parser hardening + anomaly logging)

### 2a. The crash (root cause, verified)

`app/services/prescription_parser.py::parse_medications` — when the OCR text has no `RX n`
markers (i.e. **every real pharmacy label**), the fallback puts the **entire raw OCR text** into
`frequency_text`. `Prescription.frequency_text` is `String(255)` → any real label whose OCR text
exceeds 255 chars raises `StringDataRightTruncationError` on INSERT → unhandled 500 → the user
sees the generic "retake the photo" message. The same fallback takes **line 1 as `drug_name`**,
which is why a real label yielded `drug_name = "CONESTOGA PHARMACY"` in earlier testing.

### 2b. Fix — defensive length clamp (mandatory)

Before constructing `Prescription` rows, every string field must fit its column. Do this once,
centrally (recommended: clamp inside the parser so `ParsedMedication` is bounded by
construction; column limits: `drug_name` 255, `dosage` 100, `frequency_text` 255,
`frequency_type` 30, `purpose` 100). A DB-length crash from parsed OCR text must become
impossible regardless of what OCR returns.

**Regression test (must exist):** POST a prescription whose (mocked) OCR raw_text is >1,000 chars
of realistic garbled label text → expect **201**, a saved row, no exception.

### 2c. Fix — parser hardening for real labels

In the no-marker fallback (and in `_parse_block` where applicable):

- **`drug_name` must never be a pharmacy/clinic header.** Skip candidate lines matching
  header/noise patterns (case-insensitive): `pharmacy|clinic|hospital|health (centre|center)|
  medical|dr\.|phone|fax|tel|www\.|@|postal|address`, lines that are mostly digits/punctuation,
  and lines shorter than 3 chars. Prefer the first line containing a dosage-unit match
  (`\d+(\.\d+)?\s*(mg|mcg|ml|g|iu)`); otherwise the first non-header line; final fallback
  `"Unknown medication"` (existing convention).
- **`frequency_text` must be instruction-like text, not the whole OCR dump**: keep only lines
  containing timing/instruction signals (the `timing_parser` vocabulary — daily/twice/morning/
  evening/with food/every N hours/PRN etc.), joined and capped at 255. If no such line exists,
  store an empty string, not the dump.
- Behaviour for marker-format text (`RX 1` blocks) and for `_DEMO_RAW_TEXT` must not regress —
  several existing tests encode it. If a test encodes the OLD bad fallback (whole-dump
  frequency_text or header-as-drug-name), update the test deliberately and say so in your report.

**Tests:** use two new fixtures: (i) a realistic multi-line pharmacy label text (header lines +
one medication line + instruction lines) asserting drug_name is the medication, not the header;
(ii) the synthetic test doc's text shape (5 OTC meds — see
`archive/docs/Synthetic_Prescription_Test1.png` for reference). Parser tests are pure-Python (no
OCR needed).

### 2d. The stale-text anomaly — SA investigation result + what you ship

During the deploy, the crashing request's OCR text mentioned "SPOT HOSPITAL" / "Kodamakka" —
matching NOTHING that was uploaded. The SA investigated (2026-07-27):

- **Ruled out — sidecar reuse/caching:** `dev/brains/app.py::ocr_prescription` uses fresh
  `NamedTemporaryFile`s per request, deleted in `finally`; the subprocess reads only that path.
- **Ruled out — service-worker replay:** the PWA registers `/api/**` as `NetworkOnly` with no
  background-sync plugin; a stale queued POST cannot replay.
- **Ruled out — project fixture:** the strings appear nowhere in the entire project tree
  (repo-wide grep).
- **Remaining hypotheses:** (H1) a different image genuinely reached the backend — phone-gallery
  mis-pick or file-picker glitch on Muthu's phone; (H2) a catastrophic PaddleOCR misread.
  **Decisive evidence exists:** the route saves the uploaded bytes to disk BEFORE OCR, and the
  crashed INSERT means the file is orphaned inside the `pillsafe_backend` container (no uploads
  volume → container filesystem). Muthu retrieves it (see §10, his step). That file settles H1
  vs H2 outright.

**What YOU ship (permanent attribution, either way):** in `routes/prescriptions.py` (or
`ocr_service.py`), log at INFO on every OCR call: the **sha256 (first 12 hex) and byte length of
the received image**, the saved `image_path`, and the **first ~200 chars of the returned
`raw_text`** plus its line count. One log line per scan, no image content in logs. Then any
future recurrence is diagnosable from a single log read. Also **reproduce the happy path
locally**: run backend + sidecar (`OCR_PIPELINE_ENABLED=true`), upload
`archive/docs/Synthetic_Prescription_Test1.png` through the real UI, and record in your report
the logged hash + raw_text head — this both smoke-tests Task 1 end-to-end and gives H2 a
baseline (does clean input OCR cleanly?).

---

## 3. Task 2 — Bug #2: Retake button gives a dead/black camera (root cause, verified)

`dev/frontend/src/components/CameraCapture.tsx`: the camera stream is attached to the `<video>`
element **only inside the one-time mount effect**. When a photo is captured, the preview branch
renders and the `<video>` unmounts; pressing **Retake** remounts a NEW `<video>` element that
never receives `srcObject` → permanently black viewfinder (and `cameraReady` is already true, so
not even the "Starting camera…" overlay shows).

**Fix:** re-attach `streamRef.current` to the video element whenever the viewfinder re-renders
(effect keyed on `preview === null`, or a callback ref on the video element). Also handle a
stream whose tracks have `readyState === 'ended'` (some mobile browsers kill the track while the
tab is backgrounded): detect and re-run `getUserMedia` instead of attaching a dead stream.

**Verify live** (dev servers + browser): camera → Capture → Retake → viewfinder is live again;
repeat twice; also confirm the AnalyzePage error-screen "Try Again" → fresh working viewfinder.

---

## 4. Task 3 — Bug #3: camera viewfinder vs mobile orientation

Same file. Today the viewfinder is a fixed `aspect-video` (16:9) box with `object-cover`, no
orientation/resize handling — on a phone rotation the video renders cropped/distorted. There is
also a WYSIWYG gap: capture draws the FULL `videoWidth×videoHeight` frame while the user saw a
cropped preview.

**Fix (keep it modest):** derive the container's aspect ratio from the video's actual
`videoWidth/videoHeight` (`loadedmetadata` + `resize`/`orientationchange` listeners) and render
the preview `object-contain` within a max-height, so (a) rotation reflows correctly and (b) what
the user sees is what the canvas captures. No zoom/crop features — just make display honest and
rotation-safe. Verify with browser devtools device emulation in both orientations (note in your
report that real-device rotation remains for Muthu's localhost pass).

---

## 5. Task 4 — Bug #4: fail-fast timeouts + differentiated error messages

### 5a. Backend: split connect from read (all sidecar callers)

A down sidecar currently takes as long as a slow-but-working one to fail (measured: 5-minute
spinner). Change every flat httpx timeout to `httpx.Timeout(<existing read value>, connect=5.0)`:

| File | Today | Becomes |
|---|---|---|
| `app/services/ocr_service.py` | `timeout=300.0` | `httpx.Timeout(300.0, connect=5.0)` |
| `app/api/v1/routes/pill.py` | flat `180.0` | `httpx.Timeout(180.0, connect=5.0)` |
| `app/api/v1/routes/qa.py` | flat `60.0` | `httpx.Timeout(60.0, connect=5.0)` |
| `app/services/cb4_service.py` (guard calls) | flat `20.0` | `httpx.Timeout(20.0, connect=5.0)` |

Sidecar-down must now surface in ~5s on each path. Add/adjust a test per service where a mocked
`httpx.ConnectError`/`ConnectTimeout` maps to the existing unavailable-error path (503 for OCR,
the existing degraded statuses for pill/qa).

### 5b. Frontend: three failure modes must read differently

Today sidecar-down (503 `OCR_UNAVAILABLE`), backend crash (500), and unreadable-photo all render
the same "retake the photo" text. In `AnalyzePage.tsx` (both capture handlers) and the pill path,
branch on the error payload's `error.code` / HTTP status:

- `OCR_UNAVAILABLE` / 503 → "Scanning is temporarily unavailable — the analysis service can't be
  reached. Your photo was fine; please try again in a few minutes."
- 500 / unknown → "Something went wrong on our side. Please try again."
- Genuine no-text/bad-photo outcomes keep the existing retake-in-good-lighting guidance.

All three via i18n keys, **EN + FR lockstep** (parity test must stay green). Also give the Rx
upload call an explicit axios timeout (`~330_000` ms — the api client currently has NO default
timeout, i.e. infinite).

---

## 6. Task 5 — Remove the floating assistant chatbot (full-stack) — Muthu's decision 2026-07-27

Rationale (ADR): redundant with the About/Help content and the guarded QAChatPage; it is also an
**unauthenticated public LLM endpoint** on a live site (spend/abuse surface). Removal is FULL
STACK. **Critical distinction: the app-wide browser-TTS voice feature
(`src/lib/voiceAssistant.ts`, the `voice` singleton, Navbar voice toggle, `useVoicePageAnnounce`,
dose-reminder announcements) is a SEPARATE system and MUST STAY.** Only the widget and its
speech-to-text backend go.

**Frontend — delete:** `components/AssistantWidget.tsx`; `api/assistant.ts`; its mounts in
`components/layout/PublicLayout.tsx` and `components/layout/AppShell.tsx`; its i18n keys (both
locales); its types. Sweep user-facing copy for references to the floating assistant (Help page,
About pages, KB-related mentions) and reword — the guarded "Ask" (QAChatPage) remains the one
Q&A surface. Update the stale comment in `vite.config.ts` that cites the assistant KB.

**Backend — delete:** `api/v1/routes/assistant.py` (+ its registration in `api/v1/router.py`);
`services/assistant_service.py`; `services/assistant_kb.py`; `services/voice_transcribe.py`;
`data/assistant_kb.json`; `core/rate_limit.py` (verified: its only consumers are the assistant
routes); `tests/test_assistant.py`; the `main.py` docstring mention; the faster-whisper block in
`requirements-optional.txt`; any assistant-only dependency in `requirements.txt` (check the
commented block around line 28 — if the dep it annotates, e.g. rapidfuzz, is used ONLY by
`assistant_kb.py`, remove it; if shared, keep it and fix the comment).

**Do NOT delete `services/cb4_service.py`** — it is load-bearing for the guarded `/qa/chat`
path. Remove only assistant-specific helpers inside it IF they are cleanly separable; when in
doubt, leave cb4_service untouched and note it.

**Docker note:** `dev/backend/Dockerfile` retains `libgomp1` for ctranslate2 (faster-whisper).
If, after removal, nothing in the installed requirement set needs ctranslate2/libgomp1, remove
them from the image — but ONLY if you verify by building the image and running the full suite
inside it. If you can't run that verification, leave the Dockerfile alone and flag it in your
report as a follow-up (an unused apt package is not a bug; a broken image is).

**Docs:** README, `LOCAL_TESTING.md`, and any deployment doc that mentions the assistant or
`/assistant/*` endpoints get a sweep.

---

## 7. Task 6 + Task 7 — hygiene + i18n sweep

**Task 6 (hygiene, both logged 2026-07-19):**
- Remove the fully inert `ML_PIPELINE_ENABLED` setting: the `Settings` field in
  `app/core/config.py`, its `.env.example` line, and any remaining references (grep first).
- Remove the dead `.nav-item*` CSS utilities (sole consumer was the deleted Sidebar).

**Task 7 (hardcoded-EN i18n sweep):** the known offenders (visible in FR): `TimeAwareHeader`
greetings, dashboard section labels, `AboutNav`, `PillResultPanel` copy (key-extraction only —
see non-negotiable #3), `CameraCapture` strings ("Retake", "Confirm", "Starting camera…",
"upload a photo instead", camera-denied copy), `AnalyzePage` strings ("Try Again", progress
messages, the new Task-4 error messages), dashboard hero CTA ("Analyser maintenant" mismatch).
Every new key lands in BOTH locales (parity test enforces this — update its expected count).
Grep for remaining literal EN strings in `pages/dashboard/**` and `components/**` and list any
you deliberately left (e.g. admin-only surfaces) in your report.

---

## 7a. Task 8 — Force flash/torch ON during pill-scan capture on mobile (NEW, added 2026-07-27 addendum)

**Grounding:** NB08 measured that forced illumination is the dominant lever for the imprint-OCR
failure mode that causes 83.9% of pill non-verifications (ADR 2026-07-15: dim-room imprint-up
first-shot verify DL 12/29, LED 1/14, WL 0/14 — forced flash rescues a dim room to ≈ daylight,
FLASH 6/14). That evidence is pill-imprint-specific; it does NOT extend to Rx-scan (a flat printed
document, where forced light risks glare/hotspot and has no equivalent study behind it). **Scope:
pill-scan capture only** (`mode === 'pill'` in `AnalyzePage.tsx`) — Rx-scan must NOT force light.

**Mechanism and its real limits:** `CameraCapture.tsx` captures via a live `getUserMedia` video
element + canvas `drawImage`, not `ImageCapture.takePhoto()`. The only lever for "flash" in this
architecture is the non-standard **`torch` MediaTrackConstraint** — a continuous light-on for the
duration of the stream, not a discrete per-shot strobe. Support is real but partial: Android
Chrome/Edge on hardware with a controllable LED, when the constraint's capability is present.
**iOS Safari exposes no torch/flash control via any web API — this is a platform limitation.**
Muthu's decision (this session): **silent no-op on unsupported devices**, no user-facing "flash
unsupported" notice.

**Fix:**
- Add `forceFlash?: boolean` prop to `CameraCapture` (default `false`).
  `AnalyzePage.tsx` passes `forceFlash={mode === 'pill'}` — Rx-scan passes nothing/`false`.
- After `getUserMedia` resolves, only when `forceFlash` is true: read
  `stream.getVideoTracks()[0].getCapabilities()`; if `'torch' in capabilities`, call
  `track.applyConstraints({ advanced: [{ torch: true }] })`. Wrap in try/catch — a rejected
  promise or an absent `torch` capability must be a **silent no-op** (no thrown error, no UI
  change, camera behaves exactly as it does today).
- Turn torch back off (`applyConstraints({ advanced: [{ torch: false }] })`, best-effort, errors
  ignored) whenever the stream is stopped or replaced — on unmount, and in the Task 2 (Bug #2)
  retake/stream-reattach path if it ever re-acquires a fresh stream. Do not leave a phone's
  flashlight on after the user leaves the capture screen.
- The file-upload fallback path is untouched (no live stream to control).

**Tests:** (i) `forceFlash=true` + mocked `getCapabilities()` returning `{torch: true}` →
`applyConstraints` called with `torch: true`; (ii) `forceFlash=true` + capabilities WITHOUT
`torch` → no `applyConstraints` call, no thrown error; (iii) `forceFlash` unset/false (the
Rx-scan path) → `applyConstraints` for torch is never called, verified via the `AnalyzePage`
prescription-mode render.

**Verify live:** on whatever camera the dev machine/emulator exposes, confirm the capability-check
code path runs without throwing. Real-device torch-firing verification (Android, hardware
permitting) is Muthu's localhost/device pass — note this in your report the same way Task 3 notes
real-device rotation is his to confirm.

---

## 8. Pre-registered verification bar (run ALL, then report)

1. Backend: full pytest in `dev\backend\venv` — all green; report the exact count and the delta
   story (−assistant tests, +Task 1/4 tests).
2. Frontend: `npm run type-check` and `npm run build` both clean; report the PWA precache entry
   count (it will drop after the widget removal).
3. EN↔FR key parity test green with the new key count.
4. Greps clean: `assistant` (no live code refs; docs/history mentions are fine),
   `ML_PIPELINE_ENABLED` (gone), `.nav-item` (gone), `rate_limit` (gone),
   fabricated-stats sweep over all NEW copy.
5. Decision-token freeze: `git diff` shows `success/warning/danger` tokens untouched;
   `PillResultPanel.tsx` diff is i18n-key extraction only.
6. Live smoke on the dev stack (backend + frontend + sidecar if available): (a) Capture → Retake
   → live viewfinder ×2; (b) error screen → Try Again → live viewfinder; (c) orientation via
   devtools emulation both ways; (d) sidecar STOPPED → Rx scan fails in ~5s with the
   sidecar-down message (not the retake-photo message); (e) if the sidecar is available:
   the full synthetic-doc Rx scan (Task 2d repro) → 201, plausible drug names, no crash, and the
   new OCR log line present; (f) no floating widget on landing, public pages, or dashboard;
   QAChatPage still fully works; (g) pill-scan mode's torch capability-check code path runs
   without throwing on the dev machine's camera; Rx-scan mode never attempts a torch constraint
   (code-diff/prop-wiring check is sufficient without real hardware, same standard as 6c).
7. Nothing committed (`git status` shows working-tree changes only).

## 9. For the follow-up SA verification session (do not delete)

Re-run bars 1–5 independently; browser click-through of 6a–6g at 1280 + 360, EN + FR; diff-scope
audit (only `dev/backend`, `dev/frontend`, docs, `.env.example`, README touched — `dev/brains`,
`docker/`, frozen packages byte-untouched); read the Builder Report skeptically and re-verify
every deviation it declares; then ADR entry + hand back to Muthu for commit + redeploy per
`DEPLOY_GUIDE.md` §4/§7.

## 10. Muthu's own step (not the builder's): retrieve the anomaly evidence

On the droplet, while the `pillsafe_backend` container has NOT been recreated since the deploy
session:

```bash
sudo docker exec pillsafe_backend ls -ltR uploads/prescriptions
# then, for the newest file(s) from 2026-07-27:
sudo docker cp pillsafe_backend:/app/uploads/prescriptions/<patient-id>/<uuid>.<ext> ./anomaly_upload.<ext>
```

Open the file: if it shows an Indian hospital prescription → H1 (wrong image reached the
backend; picker/gallery side). If it shows the synthetic Conestoga doc → H2 (PaddleOCR misread;
escalate to the SA — that would be a sidecar-quality finding, out of this batch's scope).

---

## Builder Report

**Executor:** Claude Sonnet 5 builder session, 2026-07-27/28. Working tree only, nothing
committed (verified `git status` at the end — see §8.7 below).

### Test counts (exact, before → after)

**Backend (pytest, `dev\backend\venv`):**

| | Count |
|---|---|
| Baseline (HEAD `115f8ba`) | 120 passed |
| + Task 1 (parser hardening + DB-crash regression) | +5 (4 in `test_prescription_parser.py`, 1 in `test_prescriptions.py`) |
| + Task 4a (sidecar-unreachable → 503 mapping, qa.py) | +1 (`test_qa.py`) |
| − Task 5 (assistant removal) | −16 (`test_assistant.py` deleted, confirmed exact count via `grep -c` on the pre-edit file) |
| **Final** | **110 passed**, 0 failed, 0 skipped |

Delta arithmetic: 120 + 5 + 1 − 16 = 110. Confirmed by running the full suite (`pytest -q`)
after every task and one final time at the end.

**Frontend:**
- `npm run type-check`: clean (no errors) — verified after every file change, not just once at
  the end.
- `npm run build`: clean. PWA precache: **63 entries baseline → 64 entries final** (measured by
  stashing all changes, building, noting the count, then popping the stash and rebuilding —
  see deviation note below on why this went *up* by 1, not down).
- EN/FR i18n key parity: **104 → 167 keys, both locales, 0 keys unique to either side** (63 new
  keys added, all in lockstep — see deviation note on how this was verified, since no test
  framework exists to run this as a real test).

**Docker (Task 5's optional `libgomp1` removal, verified per the spec's own gate — "ONLY if you
build the image and run the full suite inside it"):** built `dev/backend/Dockerfile` twice —
once unmodified (110/110 passed inside the container) and once with `libgomp1` removed from the
runtime `apt-get install` line (110/110 passed inside that container too, `python -c "import
app.main"` succeeded, and a live `docker run` answered `GET /health` with `200 {"status":"ok"}`).
Removed `libgomp1` and rewrote its stale comment. Test images deleted afterward
(`docker rmi`) — nothing left running or lingering.

### Deviations from the spec, and why

1. **`archive/docs/` is not inside the git repo — it's a sibling directory.** I initially
   reported (mid-session) that `archive/docs/Synthetic_Prescription_Test1.png` and
   `stepstakentodeploy.md` didn't exist anywhere in the tree. That was wrong: they live at
   `D:\Projects\PillSafe\archive\docs\` — a sibling of this repo, alongside the frozen
   `IMB1_v0`/`SB2`/`BB3` packages, not inside `D:\Projects\PillSafe\PillSafe\`. Once found, I
   used the real PNG for both the Task 1 test fixture (see finding #1 below) and the Task 2d
   live happy-path repro (see below). Flagging this because a future session should know the
   path convention (`archive/docs/...` in these builder prompts means "sibling of the app
   repo," not "inside it") rather than rediscovering it.

2. **No frontend test framework exists in this repo at all** (`dev/frontend/package.json` has
   no vitest/jest/@testing-library dependency, no test script, and CI (`.github/workflows/
   ci.yml`) only runs `type-check` + `build` for the frontend). This matters for two spec items
   that assume one exists:
   - **§0.7 / §8.3 "EN↔FR key parity test"** — no such test exists to "stay green." I wrote a
     small standalone Node script (kept in my scratchpad, not committed to the repo) that
     flattens both locale JSON files and diffs their key sets; ran it and confirmed 167/167
     keys, 0 missing either direction. This is real verification, just not a repo-resident,
     CI-enforced test. Recommend a minimal `vitest` setup as a fast-follow if the project wants
     this enforced automatically — I did not add one myself since standing up a whole test
     runner is bigger than a "fix batch" item and deserves its own sign-off.
   - **Task 8's three required unit tests** (torch applied when capability present; no-op when
     absent; never called when `forceFlash` is false/unset) — same gap, same reason. I verified
     all three by tracing the actual `CameraCapture.tsx` logic against each scenario by hand
     (documented inline in the component's comments) rather than writing an automated test that
     has nowhere to run. This is the one item in this batch I could not "run myself" in the
     sense §0.6 asks for — I verified it by code review, not execution, and I'm flagging that
     distinction explicitly rather than quietly calling it green.

3. **No browser was available in this session** (`claude-in-chrome` extension not connected) —
   §8.6's UI click-through items (6a Capture→Retake→live viewfinder ×2, 6b error-screen→Try
   Again→live viewfinder, 6c orientation via devtools emulation, 6f visually confirming no
   floating widget + QAChatPage click-through, 6g torch capability-check running on a real page
   load) could not be performed live. What I did instead:
   - **6d (sidecar-down fail-fast) and 6e (full synthetic-doc Rx scan) were fully verified
     live** against the real backend (and, for 6e, the real `dev/brains` sidecar — see below) —
     these don't need a browser, only HTTP.
   - **6a/6b (retake fix)** verified by code review: traced the new acquire-or-reattach effect
     (keyed on `preview === null`) through mount, capture, retake, and error-screen-remount: it
     reuses the existing stream when its track is still `'live'`, and reacquires (stopping torch
     first) when the track died. I'm confident in the logic; I have not watched a real
     `<video>` element go black-then-live in an actual browser.
   - **6c (orientation)** verified by code review only — `videoAspect` state now derives from
     `video.videoWidth`/`videoHeight` on `loadedmetadata`/`resize`/`orientationchange`, and the
     container/video use `object-contain` instead of a fixed `aspect-video` box. No visual
     confirmation.
   - **6f (no floating widget)** verified by deletion + grep, not by looking at a rendered page:
     `AssistantWidget.tsx` and `api/assistant.ts` are deleted; `PublicLayout.tsx`/`AppShell.tsx`
     no longer import or mount it; `QAChatPage.tsx` has zero references to any deleted code.
   - **6g (torch capability-check)** — same code-review verification as the unit-test gap above.
   All of the above remain for Muthu's localhost/device pass, same standard the spec itself
   already applies to Task 3's real-device rotation and Task 8's real-device torch firing — I'm
   just extending that same honest deferral to the rest of the camera-hardware-dependent checks
   rather than fabricating a pass.

4. **PWA precache count went UP (63→64), not down**, despite the spec's expectation ("it will
   drop after the widget removal"). Total precached bytes did drop slightly (3281.48 KiB →
   3275.09 KiB), so the removal registered — but Vite's route-based code-splitting apparently
   drew a different chunk boundary somewhere (likely from the new `i18n` content or the
   `PillResultPanel`/`AboutNav` prop-shape changes rippling into a different chunk split), which
   changed the *entry count* independent of net size. Reporting the actual measured number
   rather than forcing the report to match the spec's prediction.

5. **`.env.production.example` also has a stale `ML_PIPELINE_ENABLED=false` line** that Task 6
   didn't ask me to touch (only `.env.example` is named in §0.2's scope, and Task 6 says "its
   `.env.example` line"). Left it alone per the literal scope boundary; flagging it as a
   candidate follow-up since it's the same dead setting in a second file.

6. **`documentation/deployment/DEPLOY_GUIDE.md` §10.1** had a degradation-checklist row
   ("Assistant widget (project explainer + voice) — Still works, it is droplet-local") that no
   longer makes sense once the widget is gone. I removed that row (this is a historical
   deploy-run checklist, and Task 5 explicitly asks for a sweep of deployment docs that mention
   the assistant). Flagging as a judgment call on a doc that otherwise reads as a point-in-time
   log of a specific deploy session.

7. **i18n sweep scope**: I did the specifically named Task 7 offenders in full — `TimeAwareHeader`
   greetings (moved to `dashboard.greetings.*`), `AboutNav` (+ its two other consumers, `Navbar`
   and `AppFooter`, which also render `ABOUT_PAGES` and would have broken if left on the old
   `label` field), `PillResultPanel` (full key-extraction, byte-identical structure/colour —
   diff reviewed line-by-line, see §8.5 below), `CameraCapture` ("Retake"/"Confirm"/"Starting
   camera…"/upload-instead/denied copy), and `AnalyzePage` ("Try Again", the four pill-progress
   messages, the three new Task-4 error strings). I did **not** do a full site-wide i18n rewrite
   — `AppFooter.tsx`'s "Explore"/"Account"/"Sign In"/disclaimer copy and most of
   `DashboardPage.tsx`'s copy (SectionHeader labels "Safety alerts"/"Reminders", the
   no-schedule `EmptyState`, "Next dose"/"Upcoming"/"Due now"/"Past", "Unrecognized scan",
   "Reminders are on/off") remain hardcoded English. This is deliberate scope discipline (the
   task's own instructions permit "list any you deliberately left"), not an oversight — flagging
   both files as the next i18n-sweep candidates.
   - The "dashboard hero CTA ('Analyser maintenant' mismatch)" item: I investigated and could
     not find a mismatch. `dashboard.analyzeNow` is correctly wired via `t()` in
     `DashboardPage.tsx` → `TimeAwareHeader`, in both locales, with no second hardcoded/rogue
     instance anywhere in the codebase (grepped for both "Analyze Now" and "Analyser
     maintenant"). Whatever prompted this line item may already be fixed, or may only be
     reproducible live (a stale service-worker cache showing old FR copy, for instance) — noting
     as "could not reproduce statically" rather than inventing a fix for a bug I couldn't find.

### New bugs found during mandated verification

1. **The `_DOSAGE` regex false-matched postal codes**, which would have misidentified a clinic
   address line as the drug-name candidate. First occurrence: `"N2L 3G1"` matched on the bare
   "g" unit (no trailing `\b`) — caught by my own first hand-written test fixture, fixed by
   adding a trailing `\b`. Second, subtler occurrence, caught only once I found and tested
   against the **real** `Synthetic_Prescription_Test1.png`: `"N2G 1A1"` (a postal code split by
   a space, exactly as it appears on the real address line) still matched — the digit "2" inside
   "N2G" isn't glued to a following letter, so the trailing boundary alone didn't help. Fixed by
   requiring a **leading** `\b` before the digit run too (`\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu)\b`),
   which rules out a digit embedded inside a larger alphanumeric token. Full backend suite +
   both fixtures pass after the fix. This is exactly the "mandated verification catches real
   bugs" pattern the non-negotiables describe — the bug only surfaced once I tested against the
   actual synthetic document instead of a hand-invented one.

### Task 1d — anomaly investigation, what I shipped and verified live

- Shipped the permanent INFO log line in `routes/prescriptions.py` (sha256 prefix + byte length
  of the received image, saved path, raw_text line count + 200-char head) on every OCR call.
- **Reproduced the happy path locally, live, end-to-end** — this was possible after all (I'd
  initially assumed the sidecar/frozen packages weren't available in this environment; they
  are). Started `dev/brains` (`.venv` present, `IMB1_v0`/`SB2`/`BB3` all resolved,
  `torch_cuda_available: true`), started the app backend with `OCR_PIPELINE_ENABLED=true`
  (the real default), and POSTed the actual `Synthetic_Prescription_Test1.png` to
  `POST /api/v1/prescriptions` (curl, not the browser UI — no browser available, see deviation
  #3). Result: **201 Created**, no crash, `drug_name = "1. Tylenol Extra Strength
  (Acetaminophen 500 mg)"` (not the clinic header), `frequency_text` correctly clamped at 255
  chars, and the DIN-suggestion pipeline returned `TYLENOL EXTRA STRENGTH` as the top-ranked
  candidate (score 90.0) — a real, live confirmation that Task 1's fix, Task 4a's client, and
  the existing DIN-matching pipeline all still work together.
- Logged line captured: `image_sha256=8953cf13ec4a image_bytes=152730
  raw_text_lines=25 raw_text_head='Conestoga Family Health Clinic\n123 Health Street,
  Kitchener, ON N2G 1A1\nTel: (519) 555-0134 Fax: (519) 555-0135\nPatient: Muthuraj
  Jayakumar\nDate: 2026-07-27\nDOB: 1990-01-01\nPatient ID: 004821\nPrescrib'` — PaddleOCR read
  the clean synthetic document accurately (this is the H2 baseline the spec asked for: **yes,
  clean input OCRs cleanly**).
- Also measured the sidecar-down path directly against the real backend (no sidecar running,
  `BRAINS_SERVICE_URL` pointing at nothing): **2.3–2.4 seconds** to a `503 OCR_UNAVAILABLE`
  response, consistently, on two separate requests — nowhere near the old ~5-minute hang, and
  comfortably under the 5s connect-timeout ceiling (localhost connection-refused resolves
  almost instantly; a real network-level timeout would take closer to the full 5s, which is
  still the intended ceiling).
- I did **not** perform §10 (retrieving the orphaned upload from the droplet) — that's
  explicitly Muthu's step, not mine, and out of scope regardless (no droplet access from this
  session).

### Decision-freeze verification (§8.5)

- `git diff dev/frontend/tailwind.config.ts`: empty (never touched).
- `git diff dev/frontend/src/components/PillResultPanel.tsx`: reviewed line-by-line (included
  in this session's transcript) — every change is a literal-string-to-`t('pillResult.*')` swap
  or a `t`-parameter thread-through on a helper function; zero Tailwind classes, zero colour
  tokens, zero conditional/branching logic changed.
- `git diff dev/frontend/src/styles/globals.css`: only the Task 6 `.nav-item`/`.nav-item-active`
  removal (12 lines, unrelated to decision tokens).

### Scope-boundary verification (§9's future audit, done proactively)

`git status --short` at the end shows changes only under: `.env.example`, `README.md`,
`dev/backend/**`, `dev/frontend/**`, `documentation/deployment/DEPLOY_GUIDE.md`,
`documentation/integration/LOCAL_TESTING.md`. Nothing under `dev/brains/`, `docker/` (the
top-level compose directory), or the frozen sibling packages
(`D:\Projects\PillSafe\{IMB1_v0,SB2,BB3}\`) — I ran `dev/brains` locally for the Task 2d repro
but never edited anything inside it. `git status` shows a clean working tree otherwise (nothing
staged, nothing committed) — verified as the very last step.

### Fabricated-stats sweep (§8.4)

Grepped all new copy (i18n keys, log messages, comments) for stat/claim language
("fabricated"/"guaranteed"/"100%"/"clinically proven"/"FDA approved") — the only hit was the
pre-existing docstring line in `prescriptions.py` explicitly describing what NOT to do ("Honest
failure, not a fabricated prescription"), not a new claim.

### Grep sweep (§8.4)

- `assistant` (live code, case-insensitive): every remaining hit is either the `voiceAssistant.ts`
  browser-TTS module (which must stay per non-negotiable — imported as `voice` throughout) or
  generic marketing copy ("medication-safety assistant" in `AppFooter`/`AboutPage`/
  `LandingPage`, "medication-information assistant" in `cb4_service.py`'s system prompt) — never
  the removed widget/endpoints.
- `ML_PIPELINE_ENABLED`: gone from `app/core/config.py` and `.env.example`; still present in
  `.env.production.example` (deviation #5 above) and, expectedly, in this prompt file itself.
- `.nav-item`: gone.
- `rate_limit`: gone (file deleted, zero remaining references in `app/` or `tests/`).

Co-Authored by Claude Sonnet 5.
