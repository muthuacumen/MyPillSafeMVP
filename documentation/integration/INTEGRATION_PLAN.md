# PillSafe App × Brains — Integration & UI Plan

**Owner:** /pillsafe SA (Solution Architect persona) · **Started:** 2026-07-18
**Authoritative companions:** `D:\Projects\PillSafe\Brainstorm\.claude\pillsafe-adr.md` (decision log — overrides this doc on conflict) · the three package contracts (`IMB1_v0/CONTRACT.md`, `SB2/CONTRACT.md`, `BB3/CONTRACT.md` — authoritative for integration semantics).

---

## How to resume (read this first in a fresh session)

1. Activate `/pillsafe` (loads the ADR automatically).
2. Read this file. Find the first phase whose status is not ✅ DONE.
3. Spawn that phase to a **Sonnet** agent (`Agent` tool, `subagent_type: general-purpose`,
   `model: sonnet`) with: (a) the **Builder Briefing** below verbatim, (b) that phase's spec,
   (c) instructions to read the relevant CONTRACT.md files first.
4. When the agent reports: verify per the phase's verification bar, update the status board +
   the "Result" line under the phase, append an ADR entry, and stop — Muthu exits the session.

Each phase is sized to fit comfortably in one session (~45% of session tokens including
analysis + agent report + verification). Do not start a second phase in the same session
unless the first was trivial.

---

## Decisions (2026-07-18, Muthu — via AskUserQuestion, all four recommended options)

| # | Decision | Choice |
|---|---|---|
| D1 | Brains runtime | **One sidecar service** — `dev/brains/` FastAPI microservice, own py3.12 venv, host-run; app backend calls it over HTTP behind a feature flag. Frozen packages imported as sibling folders of the repo parent (`D:\Projects\PillSafe\{IMB1_v0, SB2, BB3}`), paths overridable via env. |
| D2 | Q&A voice | **CB4 built now** — BB3 retrieves + guards + assembles cited context; app-side CB4 (Claude API via existing `LLM_API_KEY` plumbing) generates the user-facing answer in the user's language. Local 7B (`BB3Engine.chat()`) retained as offline fallback when no key is set. Per ADR 2026-07-14 (F9-11 celecoxib). |
| D3 | DIN linking | **Auto-match + confirm** — at Rx-save, fuzzy-match OCR'd drug name/strength against the SB2 reference table, propose DIN, patient one-tap confirms/corrects; manual search fallback. Never auto-commit without confirmation. (SB2 CONTRACT §2 option 1.) |
| D4 | Mobile | **Responsive + PWA** — mobile-first redesign + manifest/icons/installability. No native wrapper. |

**Logo (superseded 2026-07-18, Muthu):** the old `archive\docs\PillSafeLogo.png` is RETIRED
(never copied into the app; archive copy left untouched as history). New SA-designed logo
shipped: `dev/frontend/public/{logo.svg, logo-white.svg, logo-mark.svg}` (shield + two-tone
capsule, navy #1E3A5F / teal #2A9D8F). Design tokens now seed from the PathoIntern palette
(Muthu's Phase 5 directive), NOT from the old logo.

---

## Builder Briefing (include VERBATIM in every phase's agent prompt)

1. **The three brain packages are FROZEN.** Never create, edit, or delete anything under
   `D:\Projects\PillSafe\IMB1_v0\`, `D:\Projects\PillSafe\SB2\`, `D:\Projects\PillSafe\BB3\`,
   or `D:\Projects\PillSafe\PillSafeChatbot\`. All changes live in the app repo
   `D:\Projects\PillSafe\PillSafe\`. Each package's `CONTRACT.md` is authoritative — read it
   before wiring to it.
2. **Never touch SB2's `WEIGHTS`/`THRESH` or reinterpret its decisions.** `verify`, `reject`,
   `abstain` are three DISTINCT outcomes; abstain is the COMMON case by design (safety-biased
   operating point, FA 1.15% held-out). Never collapse abstain into reject. `ranked_candidates`
   (per-attribute breakdown) and BB3's `resolution` block are mandatory to surface, not debug data.
3. **No cloud API keys in the brains sidecar** — SB2 and BB3 are local-only by design. The only
   cloud call in the whole system is CB4 (Claude) inside the app backend, using `LLM_API_KEY`.
4. **Two-process constraint:** torch and paddle can never share one process (cuDNN WinError 127).
   `imb1.analyze_pill()` already spawns its OCR subprocess internally — do not import paddle in
   the sidecar process, and do not "optimize" the subprocess away.
5. **Disclaimers are mandatory** on every decision-bearing surface: pill-scan results, Q&A
   answers, DIN confirmations. "Decision-support only — not medical advice. Verify with a
   pharmacist." The packages return a `disclaimer` field — display it, don't strip it.
6. **Machine/ops:** Windows 11, RTX 4060 8GB. No Ollama running during GPU-heavy work (the 7B
   holds ~5GB). ultralytics `predict(list)` is one giant batch — chunk it. First model load per
   process is slow; per-call latency for `analyze_pill` is seconds (Paddle subprocess spawn) —
   design UX and HTTP timeouts accordingly (≥120s).
7. **Do not commit or push.** Leave changes in the working tree; Muthu commits.
8. **Verification is not optional.** Run the phase's verification bar exactly; report actual
   outputs (counts, not adjectives). Every prior build's mandated smoke test caught ≥1 real bug.
9. Match the existing codebase's idioms (FastAPI route/service/model layering; React
   page/component/api-wrapper layering; Tailwind utility classes; existing error envelope
   `{"detail": {"error": {"code": ..., "message": ...}}}`).

---

## Status board

| Phase | Title | Status | Session date |
|---|---|---|---|
| 0 | Analysis, decisions, this plan | ✅ DONE | 2026-07-18 |
| 1 | Brains sidecar service (IMB1+SB2 online) | ✅ DONE | 2026-07-18 |
| 2 | DIN linking at Rx-save (auto-match + confirm) | ✅ DONE | 2026-07-18 |
| 3 | Pill-scan rewire (verify/reject/abstain UX) | ✅ DONE | 2026-07-18 |
| 4 | BB3 Q&A page + CB4 voice | ✅ DONE (SA independently re-verified) | 2026-07-18 |
| 5 | UI overhaul: PathoIntern design system + logo + public content chain + assistant chatbot + mobile/PWA | ✅ DONE (SA verification passed 2026-07-19; RegisterPage must-fix executed + widened to LoginPage/locales) | 2026-07-19 |
| 6 | Packaging, docs, end-to-end verification | ✅ DONE (SA independent verification passed 2026-07-19 — all suites, live E2E 1280+360, five review items evidenced; zero app bugs) | 2026-07-19 |

---

## Phase 1 — Brains sidecar service

**Goal:** IMB1_v0 + SB2 callable over HTTP from the app, contracts honored verbatim, without
touching the frozen packages or burdening the py3.11 app venv.

**Build (all inside the app repo):**
- `dev/brains/` — FastAPI service, own venv (`dev/brains/.venv`, Python 3.12; mirror the
  torch/paddle versions that IMB1_v0's README calls for — `pip freeze` from
  `D:\Projects\PillSafe\IMB1_Prototype\.venv` is the known-good reference set).
  - `config.py` — env-overridable roots: `IMB1_ROOT`, `SB2_ROOT`, `BB3_ROOT` (defaults =
    siblings of the repo's parent dir), `BRAINS_PORT` (default 8100). Roots go on `sys.path`.
  - `app.py` — endpoints:
    - `GET /health` → import status of imb1/sb2, reference row count, package paths.
    - `POST /pill/analyze` (multipart `image`, optional form `profile_dins` = JSON array) →
      runs `imb1.analyze_pill` on a temp copy; if `detected` and `profile_dins` non-empty,
      runs `sb2.match_pill`; returns `{"record": <full analyze_pill output incl. diagnostics>,
      "match": <full match_pill output or null>}`. Not-detected → `record.detected=false`,
      `match=null` (per IMB1 CONTRACT: never pass undetected records to SB2).
    - `GET /reference/search?q=&limit=` → fuzzy name search (rapidfuzz) over the SB2 snapshot's
      product/brand strings → `[{din, product, strength, score}]`. (Feeds Phase 2's
      auto-match + confirm.)
    - `GET /reference/candidates?dins=` → wraps `sb2.reference.get_candidates`, rows as JSON.
  - `smoke_test.py` — health + reference search + candidates + 2 real-photo analyses (pick 2
    rows with `verified==True` from
    `D:\Projects\PillSafe\IMB1_Prototype\results\08_derisk_imprint_up_per_photo.csv`, use each
    photo's own DIN in `profile_dins`). Assert response SHAPE strictly; report (don't assert)
    the decisions.
  - `README.md` + `requirements.txt` + `.gitignore` (`.venv/`, `__pycache__/`).
- App backend (minimal, flag-gated): `BRAINS_SERVICE_URL` (default `http://127.0.0.1:8100`) +
  `PILL_V2_ENABLED` (default `false`) in `core/config.py`; `POST /api/v1/analyze/pill/v2` in
  `routes/pill.py` — flag off → 501 `PILL_V2_DISABLED`; on → forward image + the patient's
  profile DINs (empty list until Phase 2 — use `getattr(rx, "din", None)`) to the sidecar via
  httpx (timeout 180s), return its JSON. Two new backend tests (flag-off 501; flag-on happy
  path with httpx mocked).

**Out of scope:** BB3/ollama (Phase 4), any UI change (Phase 3), DIN column (Phase 2).

**Verification bar:** (a) SB2's own pytest suite green **in the sidecar venv** (8/8);
(b) `smoke_test.py` full pass with 2 real photos end-to-end through HTTP; (c) app backend
pytest suite still fully green (40 + 2 new); (d) sidecar `GET /health` OK.

**Result (2026-07-18, Sonnet build — ALL BARS PASSED):** SB2 suite 8/8 in sidecar venv ·
smoke full pass, both real photos → `decision=verify` against their own DIN
(DIN13803 S=0.783 imprint_exact; DIN26123 S=0.784 imprint_fuzzy=1.0) · app suite **44/44**
(40 pre-existing + 4 new: flag-off 501, auth 403, mocked passthrough, unreachable 503) ·
`/health` ok (imb1_ok, sb2_ok, reference_rows=7055, torch_cuda=true) · plus a live
non-mocked end-to-end through `/api/v1/analyze/pill/v2`. **Real bug found by the smoke:**
`IMB1_v0/requirements.txt` omits two real deps of `imb1/colour.py` — `scikit-image`
(fails at import) and `scikit-learn` (fails at `analyze_pill()` call) — installed pinned to
the prototype-venv versions (0.26.0 / 1.9.0), documented in `dev/brains/requirements.txt` +
README; IMB1_v0 itself untouched (package fix is Muthu's call). **Deviation:** no Python
3.11 on this machine — both the sidecar venv and a fresh `dev/backend/venv` run 3.12; all
suites green, but CI pins may need checking. Nothing committed.

---

## Phase 2 — DIN linking at Rx-save (the project's #1 open item)

**Goal:** close SB2 CONTRACT §2 — every prescription carries a confirmed DIN, captured once at
save time. This unblocks SB2 (Phase 3) and upgrades BB3 (Phase 4 uses the `din=` bypass).

**Build:**
- Backend: `din` column (String(8), nullable, indexed) + `din_confirmed` (bool) on
  `Prescription` (+ the boot-time additive column sync the app already uses); Pydantic schemas
  updated. On prescription create (each parsed medication block), call the sidecar
  `/reference/search` with drug name + strength; attach top candidates (with scores) to the
  API response as `din_suggestions` — do NOT auto-commit any DIN.
- Frontend: after a prescription scan, a per-medication **"Is this your medication?"** confirm
  step (product name + strength + DIN, one-tap confirm / "pick a different one" search box
  backed by `/reference/search` / "skip for now"). Editing a medication exposes the same
  search. `PATCH /prescriptions/{id}` accepts `din` + sets `din_confirmed`.
- `GET /prescriptions/me` includes `din`/`din_confirmed`; profile DIN list = confirmed DINs of
  active prescriptions (this becomes `profile_dins` everywhere).
**Out of scope:** the pill-scan UI (Phase 3).
**Verification bar:** app pytest green incl. new tests (suggestion attach, din PATCH,
confirmed-DIN filtering); manual flow — scan a prescription, confirm a DIN, see it persisted
(`GET /prescriptions/me`).

**Result (2026-07-18, Sonnet build — ALL BARS PASSED, SA re-verified independently):**
backend **44 → 79 passed** (35 new: `test_din_utils` ×23 incl. leading-zero round-trip,
`test_prescription_din` ×7, `test_reference` ×4, + confirmed-DIN-filtering in `test_pill_v2`) ·
`npm run build` + `type-check` clean · live manual flow (real backend + real sidecar): create →
real `din_suggestions` (METFORMIN 500 MG → `02353377`, score 90.0, canonical form, never
auto-committed) → `PATCH {"din":"02353377"}` → `din_confirmed:true` → persisted in
`GET /prescriptions/me`; invalid DIN → 422 `INVALID_DIN`; `{"din":null}` unsets both fields;
`/analyze/pill/v2` verified live sending the real confirmed-DIN profile. **DIN format decision:**
DB stores canonical 8-digit zero-padded (`String(8)`); the SB2 token form (`DIN13803`) exists
ONLY at the sidecar boundary via the single helper `app/services/din_utils.py`
(`to_sb2_token`/`from_sb2_token`/`normalize_din`) — unconfirmed suggestions can never leak into
matching (`din_confirmed` ∩ active filter in `routes/pill.py`). Sidecar search is
failure-tolerant (3s timeout, never raises — a down sidecar degrades to empty suggestions, never
blocks the save). Frontend: reusable `DinLinkPanel` (confirm / pick-a-different-one search /
skip) on AnalyzePage post-scan + MyMedicationsPage edit, disclaimer pinned; new authenticated
`GET /api/v1/reference/search` proxy (browser never talks to the sidecar directly).
**Deviations:** manual flow used the app's demo-text Rx path — no PaddleOCR in
`dev/backend/venv` and no Rx test image in the repo (same code path
`test_upload_prescription_demo_mode` exercises); flag for Muthu: install paddleocr in the
backend venv before real-label testing. `dev/frontend/node_modules` had to be npm-installed.
Nothing committed.

---

## Phase 3 — Pill-scan rewire (verification-with-rejection UX)

**Goal:** AnalyzePage pill mode runs IMB1→SB2 through the sidecar and renders the three
decision states as first-class outcomes. Retires the OpenCV open-set path (kept behind the
legacy flag, default off).

**Build:**
- Backend: `/analyze/pill/v2` becomes the UI's pill endpoint — profile DINs now real
  (Phase 2); persist scan outcomes for Safety Records (decision, matched_din, top candidate
  breakdown); flip `PILL_V2_ENABLED` default to true.
- Frontend AnalyzePage pill mode:
  - **verify** (green): matched product name + per-attribute breakdown ("imprint matched
    exactly; colour and shape matched") from `ranked_candidates` — plus disclaimer.
  - **reject** (red): "This doesn't match any medication in your profile" — stray-pill warning.
  - **abstain** (amber, NEVER styled like reject): `ask_to_flip` → "Turn the pill over and
    photograph the other side" with one-tap re-capture; `shortlist` → top `ranked_candidates`
    by name, "Is it one of these?" confirm taps.
  - `detected: false` → "Couldn't find a pill in that photo" + capture tips (card in frame,
    flash on, flat surface).
  - Progress state during the multi-second analysis; `shadow_fusion_suspected` surfaces as a
    lower-confidence hint.
- Empty-profile case (no confirmed DINs): explain and link to prescription scan — do not run
  matching against nothing.
**Verification bar:** app pytest green; manual E2E — photo with its DIN in profile → verify
path renders; photo of a non-profile pill → reject; imprint-down photo → abstain UX. Backend
scan history row written per scan. **Bar amended by Muthu this session:** OpenCV path REMOVED
entirely (not legacy-flagged); SA manual browser click-through required; PaddleOCR backend-venv
install folded in (flag c).

**Result (2026-07-18, Sonnet build + SA independent re-verify + SA browser click-through —
ALL BARS PASSED):** Legacy OpenCV path fully deleted (`models/din_pill.py`,
`services/pill_detection.py`, `services/claude_service.py`, `tests/test_pill.py`, legacy
`/pill` route + frontend client-side compare); `/analyze/pill/v2` = the only pill endpoint,
`PILL_V2_ENABLED` default **true** (pure kill-switch). Empty-profile short-circuit (no sidecar
call — verified by sidecar log-line count + 66ms round-trip). Scan persistence: 7 additive
`analyses` columns (`detected/decision/abstain_action/matched_din/top_candidate_score/
top_candidate_breakdown/shadow_fusion_suspected`) + indexes via boot-time sync (SA watched a
fresh DB build them); `/scans/me` maps verify→matched, reject→unmatched, abstain→warning.
Frontend: new `PillResultPanel` renders all five states. **Backend pytest 79 → 84 passed**
(8 legacy tests deleted, 13 added; SA re-ran independently: 84). `npm run build` +
`type-check` clean (SA re-ran both). **PaddleOCR (flag c): 3.7.0 + paddlepaddle 3.3.1 CPU
installed; TWO real bugs found+fixed in `ocr_service.py`:** (1) paddleocr 3.x removed
`use_angle_cls`/`show_log` → ValueError silently swallowed by the generic fallback = OCR was
silently broken (result shape also changed to `OCRResult.rec_texts`); (2) CPU oneDNN crash →
`enable_mkldnn=False`. Real OCR confirmed live (real text from an Rx photo). **Agent live E2E
(real servers):** verify GRAVOL S=0.7827 imprint_exact · reject S=0.2 vs ASPIRIN-only profile ·
abstain shortlist S=0.6446 (imprint-down BENADRYL) · grey image → `detected=false` ·
empty-profile short-circuit · 4 correct scan rows. **SA browser click-through (Chrome, 2 users,
full stack live):** no_profile explain+CTA · reject red (both banners + disclaimer +
`shadow_fusion_suspected` hint surfaced live) · verify green ("GRAVOL TABLETS · 50 MG, DIN
00013803, imprint matched exactly; shape matched, colour was uncertain") · abstain amber
shortlist, candidate tap → detail + "This is not a confirmed match" warning (never
verification-styled) · not-detected + 4 capture tips · staged progress copy captured · Safety
Records page rows correct (Matched/Warning/Unmatched). **Deviations/findings:** Safety Records
"Drug Detected" column shows "Unknown" even on verify rows (doesn't render matched
product/DIN) — cosmetic, deferred to Phase 5; disclaimer modal fires per scan (by design);
orphaned `din_pills` table survives in any pre-Phase-3 DB (additive-only sync, never dropped);
no explicit opencv pin (transitive via paddlex); real-OCR latency data point: 4080×3060 Rx
label ≈ 2m21s CPU (UX/timeout implication for Rx uploads). Nothing committed (HEAD `14baabc`).
Session-external fix same day: `IMB1_v0/requirements.txt` += scikit-image 0.26.0 +
scikit-learn 1.9.0 (Muthu-authorized; flag b closed).

---

## Phase 4 — BB3 Q&A page + CB4 voice

**Goal:** "Ask about my medication" — BB3 as the only retrieval door, CB4 (Claude) as the
production voice, per D2.

**Build:**
- Sidecar: add BB3 endpoints — `POST /qa/chat` (`{message, din?, confirmed_name?}`) wrapping
  `BB3Engine.chat()` BUT with generation delegated: expose BB3's assembled scoped context +
  guard outcomes so the app can hand them to CB4. Concretely: sidecar returns the full BB3
  response (all 8 statuses verbatim) **plus** the packed cited context; the app backend's new
  `cb4_service.py` calls Claude (existing `LLM_API_KEY`) with a fixed system prompt (answer
  ONLY from the provided cited context; answer in the user's language; carry citations;
  abstain when the context doesn't cover it) and replaces the local-7B answer text when a key
  is present. No key → local-7B answer passes through, marked "offline fallback". BB3's
  deterministic guards run regardless of voice.
  ⚠️ Requires `ollama serve` + `qwen2.5:7b-instruct` for the fallback path only; document.
- App backend: `POST /api/v1/qa/chat` (patient-scoped; passes profile DINs for a "my
  medications" quick-ask; DIN bypass when the user taps a specific medication).
- Frontend: chat page — `confirm`/`pick_list` as real button flows (never auto-picked),
  `not_found`/`no_entity`/`refused_dosing`/`guard_refused` distinct rendering, sources/DIN
  chips visible, disclaimer pinned. Entry points: sidebar + "Ask about this" on each
  medication card (DIN bypass) + post-scan verify screen.
**Verification bar:** BB3 pytest green in sidecar venv (29/29); scripted Q&A smoke (resolved /
confirm / pick_list / not_found / refused_dosing each hit once, statuses asserted); CB4 path
answers celecoxib-class question consistently WITH its cited contraindication (spot-check);
app pytest green.

**Result (2026-07-18, Sonnet build — AGENT BAR PASSED IN FULL; SA independent re-verify
DEFERRED to next session by Muthu's direction):**

*Architecture as built (SA design, no frozen file edited):* sidecar gained **context mode** —
`dev/brains/qa.py` mirrors `BB3Engine.chat()`'s pre-generation flow field-for-field by importing
the frozen package's own functions (`resolver`/`enumerate`/`retrieve`/`guards` + verbatim packing
constants and `PROMPT_TEMPLATE` from `bb3.engine`), stopping where generation would start and
returning `status: "context_ready"` + packed cited context + enum schema + entity names. Context
mode never instantiates `BB3Engine` (so no Ollama requirement on the CB4 path); `mode=full` is
the local-7B offline fallback (lazy engine, 503 when Ollama down). New sidecar endpoints:
`POST /qa/chat`, `POST /qa/guard` (single-shot `entity_guard_violation` /
`ingredient_consistency_violation` / `abstention_consistency_violation` on the CB4 answer —
the production voice is guarded, not just the local one; retry protocol lives app-side,
one corrective retry then `guard_refused`, mirroring `guards.check_and_fix`). App backend:
`app/services/cb4_service.py` (anthropic SDK 0.40.0→**0.117.0**, `LLM_MODEL` default
**`claude-haiku-4-5`** — Muthu's call this session, env-overridable), `POST /api/v1/qa/chat`
(auth'd; DIN boundary via `din_utils`; BB3's exact output shape + `voice`/`model` fields).
Frontend: `QAChatPage` (all 8 statuses distinct; confirm/pick_list real button flows;
source/DIN chips; voice badge; language selector en/fr/es/ar/ta; disclaimer pinned) + entry
points: sidebar, "Ask about this" on confirmed-DIN medication cards, pill-scan verify panel.

*Agent-reported verification (all run):* BB3 pytest **29/29** in sidecar venv (134.9s) ·
parity check **6/6 empty diff** (confirm/pick_list/not_found/no_entity/enumeration/
refused_dosing — context mode ≡ frozen engine) · HTTP smoke **7/7** statuses incl.
`context_ready` (warfarin: packed_sources 15,235 chars, offered_tags non-empty) · offline
fallback live (`voice=local_7b`, answered/abstained) · backend pytest **93/93** (84+9 new) ·
`npm run build` + type-check clean · **Live CB4 E2E (real key, claude-haiku-4-5):**
(a) warfarin-food → honest abstention (retrieval-recall-bound — top-5 chunks were
CYP450/drug-drug; the known F9 usefulness gap, not a Phase 4 bug); (b) **F9-11 celecoxib →
"No. According to the product monograph, celecoxib is contraindicated if you have demonstrated
allergic-type reactions to sulfonamides…" cited [DIN:2239942]/contraindications — CORRECT
polarity where the local 7B inverted it; the CB4 architecture decision validated at the
cheapest D2-compliant tier**; (c) French request → correctly localized abstention.

*Bug found in frozen BB3 (documented `dev/brains/README.md`, NOT fixed — package frozen):*
resolver treats **"daily"** as a distinctive brand token, so phrasings like "maximum daily
dose of X" pollute the resolved DIN set and can silently defeat the dosing-refusal gate for
no-PM products. Same failure class as F9-16 ("constipation"→"ACTION"). Added to BB3's owed
guards list as **F9-17** alongside WP2.5/WP3/F9-16/F9-04.

*Deviations:* CB4 abstention string is translated when a non-English language is requested
(PROMPT rule 1 says the exact English string; model translated — reads as more correct for
the product, tighten later) · Claude `stop_reason: "refusal"` not specially branched (falls
into the safe JSON-degeneracy retry path) · frozen packages verified untouched via mtime
diff · nothing committed.

**SA independent re-verification (2026-07-18, follow-up session — ALL BARS PASSED, status
flipped ✅):** backend pytest **93/93** (33.3s) · BB3 pytest **29/29** in sidecar venv (81.3s) ·
`parity_check.py` **6/6 empty diff** (Ollama up) · `npm run type-check` + `build` clean ·
sidecar `/health` ok (imb1/sb2/bb3 all ok, reference_rows=7055, torch_cuda=true) · **live
celecoxib re-run** through the real stack (register → `POST /api/v1/qa/chat`): status
`answered`, `voice=cb4`, `model=claude-haiku-4-5`, answer "No. The reference documents state
that celecoxib is contraindicated if you have demonstrated allergic-type reactions to
sulfonamides…", `cited_tags=[DIN:2239942]` (contraindications), all `guard_flags` false ·
**SA browser click-through** (Playwright driving installed Chrome headless, 1280×900; fresh
user seeded via the Phase 2 flow — demo Rx → suggestion `02353377` score 90 → PATCH-confirmed):
confirm flow ("Yes, I meant metformin" / "No" real buttons; never auto-picked) → CB4 answer
with `claude-haiku-4-5` voice badge + 5 DIN chips + pinned disclaimer · pick_list
(escitalopram / citalopram buttons) → tap → honest CB4 abstention · not_found (Coumadin →
strict "not in Canadian formulary") · no_entity (headache → condition-only refusal) ·
refused_dosing (benadryl → amber ShieldAlert card, dosing hard gate) · enumeration
(acetaminophen → deterministic DIN-cited list with "…and 93 more" truncation + Rx-class
exclusion note) · **French**: "warfarine" → confirm → click-through → French CB4 answer with
DIN 2245618 chip · **DIN bypass** from the My Medications card → "Asking about Metformin HCl
500mg (DIN 02353377)" header + scoped ask. `guard_refused` not UI-triggered (needs a double
guard violation — not deterministically reachable; covered by backend tests + rendering code
review). Disclaimer modal ("I Understand") fires per page by design; screenshots in session
scratchpad.
*Observations (no Phase 4 bugs):* (1) DIN-scoped "what are the side effects" hits BB3's
empty-retrieval abstention short-circuit (`voice=none`) while the ingredient-scoped metformin
ask answers richly across 30 DINs — frozen-BB3 **WP3** routing-gap evidence ("side effects"
doesn't lexically reach the adverse-reactions section at single-DIN scope); safe, correctly
rendered, strengthens WP3's priority. (2) Each answer makes 3× `/qa/guard` calls (entity loop +
ingredient loop + final structural check) — by design, could collapse to one call as Phase 5/6
polish. (3) Confirm/short-circuit strings stay English under a non-English language selection
(BB3's deterministic `voice=none` strings; only CB4 output localizes) — product-copy decision
deferred.

---

## Phase 5 — UI overhaul: PathoIntern design system + logo + public content + assistant + mobile/PWA

**Scope EXPANDED 2026-07-18 (Muthu's directives, this session):** (1) palette = PathoIntern's
(navy #1E3A5F primary, teal #2A9D8F, coral #D64045, burnt #E76F51, light #E8EEF2 — reference:
`D:\Projects\PathoIntern_MVP\frontend\`); (2) new SA-designed logo, old logo retired;
(3) PathoIntern-style public content chain: Landing/Introduction → About → Vision & Mission →
Problem Statement → Scientific Foundation → Team (5 members, roles SA-assigned per Muthu's
authorization) with AboutNav prev/next; (4) floating PillSafe Assistant chatbot at FULL
PathoIntern parity (project-explainer scope, EN/FR, confidence zones, voice via faster-whisper
STT + browser TTS, CB4 generation, med-questions redirect to the guarded Q&A);
(5) **QAChatPage STAYS** — SA push-back accepted rationale: it is the only surface of the
BB3→CB4 stack; the explainer widget refuses medication content by design; (6) original scope
kept: mobile-first + PWA + Safety Records "Drug Detected" cosmetic fix. Binding: `success`/
`warning`/`danger` decision tokens byte-identical; coral never on decision surfaces.

**Grounding (SA, verified this session):** NLM Pill Image Recognition Challenge (Yaniv et al.,
IEEE AIPR 2016, DOI 10.1109/AIPR.2016.8010584 — winner top-5 43%); MobileDeepPill (Zeng, Cao
& Zhang, MobiSys 2017, DOI 10.1145/3081333.3081336); Few-Shot Pill Recognition (Ling et al.,
CVPR 2020, DOI 10.1109/CVPR42600.2020.00981); CIHI Drug Use Among Seniors in Canada (1 in 4
seniors on 10+ drug classes; ~5× ADR hospitalization at 10+). Previously verified: ePillID,
GO-PILL, MedSnap, Hanley & Lippman-Hand 1983. Dev-set metrics stay OFF public copy.

**Prep DONE this session (all durable, in working tree):**
- `documentation/integration/phase5_content_pack.md` — ALL public-page copy + widget strings
  (SA-authored, citation-verified; builder transcribes verbatim).
- `dev/backend/app/data/assistant_kb.json` — 30-entry assistant KB (EN answers + FR question
  aliases; CB4 localizes).
- `dev/frontend/public/{logo.svg, logo-white.svg, logo-mark.svg}` — new brand mark.
  **(RETIRED 2026-07-19 — deleted; replaced by Muthu's own logo + the MyPillSafe rebrand, see Result.)**
- `documentation/integration/phase5_builder_prompt.md` — the COMPLETE builder prompt +
  next-session resume steps (incl. Muthu's Journey.md-harvest directive: SA lifts intro-worthy
  material from `D:\Projects\PillSafe\Journey.md` into pack §1/§2 BEFORE spawning).

**Build status:** BUILT 2026-07-19 by a Sonnet agent (full run; the 2026-07-18 spawn had been
stopped within seconds on token budget with no files written). See Result below.

**Verification bar:** backend pytest fully green (was 93; + new assistant tests incl. zones,
med-redirect, rate-limit 429, voice) · `npm run type-check` + `build` clean · PWA manifest +
SW in build output, installability check · live smoke: real CB4 `/assistant/chat`, med-intent
redirect, clarification + fallback zones, `/assistant/voice` with a generated WAV · decision
tokens diff-clean vs HEAD · SA browser click-through at 360/1280px (landing, all 5 about
pages, widget flows, PillResultPanel states unchanged).

**Result (2026-07-19 — BUILT; agent verification bar fully passed; SA independent verification PENDING, next session):**

**Pre-build SA amendments (same session, Muthu's two AskUserQuestion calls):** Muthu supplied his
own logo (`dev/frontend/public/MyPillSafe_Logo.png`) → (1) **app-surface rebrand to "MyPillSafe"**
(dev packages / ADR / paper keep "PillSafe"); (2) **white rounded chip behind the logo on all dark
surfaces** (wordmark + mark linework are navy). SA asset forensics: the PNG's "transparency" was a
baked-in fake checkerboard (alpha=255 on 100% of pixels, generator artifact); a pure color-key was
measured unsafe (top capsule highlight is cool, R−B ≈ −22, same signature as the checker) → cleaned
via connected components (border-connected pale-cool → transparent, 994,008 px; enclosed → pure
white, 2,486 px / 13 components), alpha feathered. Derived `logo.png` (653×521 lockup) +
`logo-mark.png` (400×400 mark); source PNG untouched; three prep SVGs deleted. Content pack renamed
(44 occurrences), assistant KB renamed (48; `"author": "PillSafe SA"` preserved; JSON validated).
`phase5_builder_prompt.md` amended (briefing #10 brand-sweep rule, §B rewrite, maskable icon
background navy→WHITE, brand-sweep grep added to the bar). **Note:** the KB / content pack /
builder prompt showing as modified in `git status` (and the 3 SVG deletions) are this SA prep, NOT
builder writes — the builder never edited them.

**Agent-run verification bar — ALL PASSED (agent-reported):**
- Backend pytest **109 passed** (was 93; +16 in new `tests/test_assistant.py`), 0 failures.
- `npm run type-check` + `npm run build` clean; `dist/manifest.webmanifest` + `sw.js` +
  `workbox-*.js` present (64 precached entries); icon script generated favicon-32 /
  apple-touch-icon / pwa-192 / pwa-512 / pwa-maskable-512.
- Live smoke (servers killed after): (a) real CB4 `/assistant/chat` "What is MyPillSafe?" →
  `used_llm: true`, confidence 100, on-scope answer; (b) "can I take ibuprofen with warfarin?" →
  `redirect_to_qa: true`, `used_llm: false`, no LLM call; (c) clarification zone (conf 45.45,
  3 options) + fallback zone (conf 33.8, verbatim string); (d) System.Speech WAV "What is My Pill
  Safe" → `/assistant/voice` → `{"text":"What is my pill safe?"}`.
- Frozen decision tokens `success/warning/danger` byte-identical vs HEAD; `PillResultPanel.tsx`
  **zero diff**.
- Brand sweep: one remaining non-"MyPillSafe" occurrence = a code comment in `DashboardPage.tsx`
  (not user-visible).
- Nothing committed (~31 modified, ~24 untracked, 3 SA-deleted SVGs).

**Builder deviations (SA-reviewed, none block verification):** teal scale redefined to derive from
#2A9D8F + `primary`→navy remap — cascade restyle of all pre-existing pages instead of file-by-file
rewrites (spec-permitted); custom ~70-line unit-tested sliding-window rate limiter instead of
slowapi; **med-intent gate is keyword-broad by design** — "take"/"prendre" alone trigger it, so
even "Does MyPillSafe remind me to take my medication?" redirects to the guarded Q&A instead of
answering from the KB (SA accepts: the false positive errs toward the guarded path, consistent
with abstain-over-guess; revisit only on real UX pain); camera full-bleed partial (inner
viewfinder keeps rounded corners); app has no sidebar-collapse state so `logo-mark.png` is
icons-only; `cb4_service.py` gained brand-name strings (app-generated text, in-scope per the
brand-sweep rule — Phase 4 QA tests still green in the 109).

**SA verification (2026-07-19) — ALL BARS PASSED; status ✅ DONE:**

1. **Suites re-run by the SA:** backend pytest **109 passed** · `npm run type-check` +
   `npm run build` clean (build re-run AFTER the must-fix edits below) · PWA artifacts in
   `dist/` (sw.js + workbox, 64 precached entries; manifest verified clean UTF-8).
2. **MUST-FIX executed and WIDENED** — the builder-reported RegisterPage violation was one
   instance of a class; a full-frontend grep sweep (`100K|100,000|95%|12+|thousands|HIPAA|
   Bank-level|Deaths prevented`) found the rest. Removed: RegisterPage stats
   ("100K+ Deaths prevented", "95%+ Accuracy", "<5s", "12+ Languages") + "Join thousands"
   headline + "Bank-level encryption"/"HIPAA-aware" claims; LoginPage's **nonexistent
   "Drug Interaction Checker" feature card**, "12+ languages" claim, and same
   encryption/HIPAA chips; `auth.brand` in **both** en.json/fr.json — "Preventing 100,000+
   annual medication errors" and a **fabricated caregiver testimonial with fabricated
   attribution**. Replaced with pack-compliant copy: CIHI stat tiles (1-in-4, ~5×), the
   three-outcome + EN·FR tiles, real feature descriptions (scan/verify/cited answers),
   "Capstone MVP · Decision-support only" chips, and the "Built to warn, designed to
   abstain, never to guess" principle card in place of the testimonial. Remaining sweep
   hits verified true-or-CSS (ProblemPage "thousands of candidate products" = the 7,055-DIN
   formulary; QAChatPage `max-w-[95%]`).
3. **Browser click-through** (Playwright driving installed Chrome, live 3-server stack,
   360×740 AND 1280×800): 48 scripted checks — 46 PASS, 2 FAIL both traced to the SA
   script itself (its panel locator bound to LandingPage's decorative `div.w-80` blur
   circle instead of the widget panel; screenshots prove both flows correct — the
   mandated-verification-finds-a-bug pattern struck the verifier again, same as Phase 4's
   scroll false alarm). Verified: landing + all 5 about pages + AboutNav chain at both
   widths; **no horizontal scroll on any page at 360px**; widget high zone = live CB4
   answer (badge `High 100% · EN · 7.62s · Show sources (3)`); med-intent
   "ibuprofen with warfarin" → redirect button (no direct answer); fallback = verbatim
   string (`Low 33% · (fallback)`); EN/FR toggle; auth pages render the new copy (CIHI
   tiles screenshot-confirmed at 1280); dashboard + BottomTabBar at 360 (widget bubble
   clears it); seeded meds visible with "Linked to DIN 00013803" chip; QAChatPage intact
   with widget hidden; AnalyzePage renders; `PillResultPanel.tsx` zero diff vs HEAD
   (code-level, from the agent bar — decision surfaces untouched). WCAG contrast:
   white/60·/70·/80 over navy #1E3A5F = **5.25 / 6.53 / 7.99 : 1**, all ≥ 4.5:1.
4. **Voice round-trip re-run live:** System.Speech WAV → `POST /assistant/voice` →
   `{"text":"What is my pill safe?"}`.
5. **PWA:** manifest installable (name/short_name MyPillSafe, standalone, navy theme,
   192 + 512 + maskable-512 icons); `/api/**` = NetworkOnly runtime handler **and**
   navigateFallbackDenylist — no offline-API pretense.
6. **Test fixtures for Muthu's independent pass:** 5 patient accounts seeded via the app's
   own models (real login path), 3 confirmed-DIN prescriptions each = all 15 NB07 OTC
   DINs. Credentials + launch steps + suggested flows:
   **`documentation/integration/LOCAL_TESTING.md`** (Phase 6 folds this into the README).

*Observation (pre-existing, Phase 6 polish):* the dashboard stat card **"Interactions
Found"** implies an interaction-checker the app does not have (same class as LoginPage's
removed feature card) — rename or remove in Phase 6.

---

## Phase 6 — Packaging, docs, end-to-end verification

**Goal:** reproducible run story + honest docs.

**Build:** brains sidecar joins the run story (docker-compose extra-host pointing at the
host-run sidecar — GPU stays on host; document why it's not containerized), `Makefile`
targets, README rewrite (architecture diagram now five-brain-accurate, setup steps, feature
flags), `.env.example` refresh, Journey.md gets an integration chapter (SA writes, not
Sonnet), final full-stack E2E: register → scan Rx → confirm DINs → scan pill (verify + reject
+ abstain) → ask Q&A (CB4) → records — on desktop AND a phone-sized viewport.

**Muthu's verification items (added 2026-07-19, after his Phase 5 review — each must be
checked/fixed during Phase 6):**
1. **Science page paper links** — every paper cited in `/about/science` (Scientific
   Foundation) must link out to the actual paper (DOI/arXiv/publisher page); verify each
   link resolves to the correct paper (verified DOIs are in the Phase 5 Grounding block
   above — never link an unverified citation).
2. **Public footer** — every public page footer reads:
   `MyPillSafe · 2026 · Muthuraj Jayakumar, Sumanth Reddy, Lohith Reddy, Ali Ozdemir,
   Abdullah Mohammed`.
3. **Team page roles** — `/about/team` shows each member's role WITH their tasks/
   responsibilities outlined, at PathoIntern parity (role title + concrete task list per
   member, not just names).
4. **Dashboard palette drift** — the dashboard's UI colours must match the Phase 5
   navy/teal system; the dashboard greeting header's bright-blue gradient is off-palette
   (visible in the Phase 5 click-through screenshot `m360_dashboard.png`). Sweep the
   dashboard pages for remaining pre-Phase-5 blues. Binding constraint unchanged:
   `success`/`warning`/`danger` decision tokens stay byte-identical — palette fixes must
   never touch decision surfaces (PillResultPanel etc.).
5. **Dashboard menu re-assessment (label intuitiveness)** — Muthu's example: how would a
   patient know **"Analyze Medication"** is where you scan a pill before taking it?
   Revisit EVERY dashboard nav option, validate its purpose, rename to plain
   **task-language a senior would recognize** (what the user is trying to DO, not what
   the system does). Current inventory (en.json `nav.*` + `nav.short.*` for the
   BottomTabBar): Dashboard/Home · **Analyze Medication/Analyze** · My Medications/Meds ·
   Ask about my medication/**Q&A** · My Profile · **Safety Records/Records** ·
   **Med Education** · Settings. Flagged by the SA as least self-explanatory: "Analyze
   Medication" (candidate direction: "Check My Pill"/"Scan Pill"), "Q&A" short label
   (the sidebar's "Ask about my medication" is the model — the short form lost the
   meaning), "Safety Records" (it is the scan history), "Med Education". Rules:
   renames are **label/i18n-only** (EN + FR in lockstep; never rename routes, code
   identifiers, or API fields — Phase 5 brand-sweep precedent); keep labels short enough
   for the 5-tab bar at 360px; decision-surface wording untouched. Verification: each
   final label passes a naive-reader test ("would a first-time senior know what happens
   when they tap this?") documented per label in the Phase 6 Result.

(Also carried from Phase 5: rename/remove the dashboard "Interactions Found" stat card —
implies an interaction-checker the app doesn't have.)

**Verification bar:** all suites green (app, SB2 8/8, BB3 29/29 in sidecar venv); the E2E
script above executed and logged in this doc; Muthu's four items above each verified with
evidence (link-check output, footer screenshot, team-page screenshot, dashboard
before/after screenshots).

**Result (build session 2026-07-19 — SA verification DEFERRED to next session, Muthu's token-budget call):**

**Muthu's four scope calls this session (AskUserQuestion):** (1) delete ALL legacy groups from
the app repo root; (2) PROGRESS.md deleted (plain-language audience now served by the About
chain + assistant); (3) cloud deploy KEPT as app-only demo (render.yaml/vercel.json stay,
documented as brains-disabled); (4) **README = number-free** (treated as public copy —
qualitative only; measured numbers live in Journey.md + the contracts. BINDING for future
README edits.)

**SA-side work (done this session):**
- **Legacy purge executed** (12 items): presentation.md, sprint0-README.md, PROGRESS.md,
  documentation/sprint0-notes.md, orchestrator.ipynb, data-collection/, training/,
  streamlit_app.py, st_db.py, st_pages/, .streamlit/, root requirements.txt. Pre-delete
  sweep: render.yaml/CI/Makefile reference none. Dangling refs fixed:
  requirements-optional.txt PILLSAFE_BUILD.md comment; .gitignore `.venv-streamlit/`.
- **README.md rewritten from scratch** — five-brain-accurate diagram + brain table, sidecar
  run story (3 terminals), flags table matching config.py, API overview incl. sidecar
  endpoints, docker + app-only cloud deploy section, number-free limitations, LOCAL_TESTING.md
  linked, CI badge repointed to the real remote (muthuacumen/mypillsafe — old badge pointed at
  a dead repo).
- **Journey.md §12 written** (app-integration chapter, Phases 1–6 narrative + §9 status
  pointer: #1/#2 closed, #3 gained F9-17).

**Builder results (Sonnet agent; full report in its transcript, condensed here):**
- **Item A (science links):** all 6 verified citations link out (NLM Challenge, MobileDeepPill,
  ePillID, Few-Shot, GO-PILL, CIHI — URL+title table in builder report). MedSnap + Hanley
  deliberately left unlinked (outside the closed VERIFIED set).
- **Item B (footer):** exact five-name string in AppFooter.tsx.
- **Item C (team page):** per-member "Responsibilities" task lists added, task-language only.
- **Item D (palette):** root cause found — `lib/timeOfDay.ts` afternoon hero gradient was
  sky/blue (screenshot was an afternoon capture); fixed + night indigo + 4 more off-palette
  spots + 2 dead blue hex tokens (`evening`/`night`) in tailwind.config.ts. Post-fix grep of
  dashboard pages for blue/indigo/sky: zero live occurrences. **Decision tokens byte-identical;
  PillResultPanel.tsx zero diff (confirmed).**
- **Item E (nav labels, EN/FR lockstep, naive-reader table in builder report):**
  Analyze Medication→**Check My Pill** (short **Check Pill** / FR Vérifier ma pilule),
  Q&A short→**Ask** (FR Demander), Safety Records→**Scan History** (short **History** / FR
  Historique des scans), Med Education→**Medication Guide**; Dashboard/Home, My Medications/
  Meds, My Profile, Settings kept. Also aligned stale `dashboard.actions.*` quick-action tiles
  + one hardcoded English tile (deviation, accepted — same-page label consistency).
- **Item F:** "Interactions Found" → **Pills Verified**, computed from real scan records
  (match_status==='matched'); old keys removed, no dangling references.
- **Item G (packaging):** docker-compose gains extra_hosts + BRAINS_SERVICE_URL=
  host.docker.internal:8100 + 3-reason not-containerized comment (YAML validated; docker not
  run — honest report); Makefile gains brains/backend/frontend/test-backend/seed local targets
  (tabs verified; `make` not on PATH to dry-run); .env.example fully synced to config.py
  (16 fields; removed dead REDIS_URL/AUTH_RATE_LIMIT/POSTGRES_*; fixed stale
  ACCESS_TOKEN_EXPIRE_MINUTES 15→60, OCR default, LLM_MODEL→claude-haiku-4-5, CB4-accurate
  key comment).
- **Agent-run verification:** backend pytest **109 passed** · type-check + build clean (64
  precached PWA entries) · EN↔FR key parity zero missing · locale/diff/grep gates above.
- **Out-of-scope findings (builder, not fixed):** (a) `/api/v1/analyze` legacy stub
  (hardcoded demo Metformin) still mounted — dead code, superseded by /analyze/pill/v2;
  (b) unused `analyze.*` i18n block ("Sprint 4" copy) in both locales; (c) AppShell
  `pageTitleKeys` missing `/dashboard/qa` (blank Topbar title; ties into a pre-existing
  duplicate-H1 pattern on all dashboard pages).

**➡ NEXT SESSION (SA independent verification — do NOT re-spawn the build):**
1. Re-run suites: backend pytest (expect 109), frontend type-check + build, SB2 8/8 + BB3
   29/29 in the sidecar venv (builder could not run those), sidecar /health.
2. Full-stack E2E on the live 3-server stack per the Phase 6 spec: register → scan Rx →
   confirm DINs → pill verify + reject + abstain → Q&A (CB4, incl. one FR answer) → Safety
   Records ("Scan History") — desktop 1280 AND 360px viewports, screenshots.
3. Muthu's five items, evidence each: click all 6 science links live (correct paper loads);
   footer screenshot; team-page screenshot; dashboard after-screenshots at 360 across ≥2
   time-of-day gradients (the fix lives in timeOfDay.ts — check afternoon specifically);
   nav labels at 360px (5 tabs fit: Home/Check Pill/Meds/Ask/History + FR lengths in sidebar).
4. Re-confirm: decision tokens byte-identical, PillResultPanel.tsx zero diff, tailwind
   evening/night hex change reviewed and accepted/reverted.
5. README (SA-written concurrently with the build) cross-checked against builder's
   .env.example/Makefile/compose — flags table and make targets must match; ASCII-diagram
   nav wording updated to the new labels if it grates.
6. Rule-of-thumb sweep: no fabricated-claims regression on TeamPage task lists.
7. On pass: flip status board to ✅ DONE, drop the "verification pending" note from
   Journey.md §12, ADR completion entry. Decide with Muthu: delete the legacy /analyze
   stub + dead analyze.* i18n block + fix /dashboard/qa Topbar title (5-minute items, or
   log as post-capstone polish).

**SA verification Result (2026-07-19 — ALL BARS PASSED; status flipped ✅ DONE):**

1. **Suites re-run by the SA:** backend pytest **109 passed** · frontend type-check +
   `vite build` clean (64 precached PWA entries) · SB2 **8/8** in the sidecar venv · BB3
   **28 passed + the Ollama-gated smoke run live = 29/29** (Ollama started for the test,
   stopped before any pill analysis per the GPU-contention constraint) · sidecar `/health`
   ok (imb1/sb2/bb3 all true, reference_rows=7055, CUDA available).
2. **Live E2E (Playwright driving installed Chrome, 3-server stack), desktop 1280×800 +
   mobile 360×740, screenshots in session scratchpad `shots/`:** fresh-account register →
   Rx label upload → OCR → **5 DIN suggestions → one-tap confirm → PATCH persisted
   `din_confirmed=true`** (never auto-committed) · as `margaret@test.com`, all three pill
   outcomes through the UI against her real confirmed profile: **verify** (GRAVOL DL photo,
   matched DIN13803), **abstain → ask_to_flip** (GRAVOL LED photo — the flip prompt renders),
   **reject** (SENOKOT photo, red warning) — photos pre-screened via the sidecar so each
   outcome was deterministic · Q&A: **F9-11 celecoxib probe re-passed live**
   ("No … contraindicated … allergic-type reactions to sulfonamides", `voice=cb4`,
   `cites=[DIN:2239942]`) and **French warfarine answer** (`voice=cb4`,
   `cites=[DIN:2245618]`, French prose) · "aspirin with food" produced CB4's **honest
   uncited abstention** (`abstained=true`, "I don't have that information…") — the known
   F9 retrieval-recall gap, same class as Phase 4's warfarin-food, not a regression ·
   Scan History shows Matched/Warning/Unmatched rows · no horizontal scroll at 360 on
   landing/dashboard/analyze/qa/safety/science, EN and FR.
3. **Muthu's five items, evidence each:** (1) **six science links** — arXiv ePillID and
   CIHI loaded live with correct titles; IEEE×2/ACM/MDPI returned automation bot-walls, so
   resolved out-of-band: doi.org handle API maps 10.1109/AIPR.2016.8010584 →
   ieeexplore/8010584, 10.1145/3081333.3081336 → dl.acm.org, 10.1109/CVPR42600.2020.00981 →
   ieeexplore/9157392, and WebSearch confirms mdpi.com/2227-7390/14/2/356 is "GO-PILL: A
   Geometry-Aware OCR Pipeline…" — all six point at the verified papers (a human browser
   passes those bot-walls). (2) **footer**: five-name string live (`d02_footer.png`).
   (3) **team page**: five members with task-language Responsibilities lists
   (`d12_team.png`), zero fabricated claims. (4) **palette**: gradients checked live in
   all four time slots (afternoon teal by wall-clock AND mocked clock, morning amber,
   evening orange/rose, night navy) at 1280 and 360 with **zero sky/blue/indigo classes**
   on the dashboard; "Pills Verified" card present, "Interactions Found" gone.
   (5) **nav labels**: 5-tab bar fits at 360 with no overflow in EN
   (Home/Check Pill/Meds/Ask/History) and FR (Accueil/Vérifier/Médicaments/Demander/
   Historique); sidebar shows the full renamed set in both languages, no clipped labels.
4. **Static re-confirms:** decision tokens byte-identical (unchanged context lines in the
   tailwind diff vs `bc27af8`); `PillResultPanel.tsx` **zero diff**; the tailwind
   `evening`/`night` hex change reviewed — consumed only by the unused
   `TIME_SLOT_PAGE_WASH` export (single reference = its own definition) — **accepted**.
5. **README cross-check:** config.py's 16 Settings fields match `.env.example` exactly;
   README flags table consistent (incl. `ACCESS_TOKEN_EXPIRE_MINUTES=60`,
   `LLM_MODEL=claude-haiku-4-5`); Makefile targets as documented; compose `extra_hosts` +
   `host.docker.internal:8100` override present; CI badge → real remote
   (muthuacumen/mypillsafe) and CI pins Python 3.11 as stated. One fix applied: the README
   ASCII diagram still carried pre-rename nav labels — updated to
   Check My Pill / Ask (Q&A) / Scan History / Medication Guide (box widths preserved).
6. **Fabricated-claims regression grep** across `dev/frontend/src`: only hit is a CSS
   `max-w-[95%]` utility — clean.
7. **No app bugs found.** Every E2E failure traced to the SA's own scripts (the AppShell
   first-visit disclaimer modal blocking clicks, an orphaned waitForResponse promise, the
   17:00 afternoon→evening boundary crossing mid-run, `selectOption('fr')` vs the real
   option value `'French'`, and a case-sensitive innerText check against CSS-uppercased
   text) or to publisher bot-walls — the Phase 4/5 verifier-bug pattern, five more times.
   *Honest observations, no action required:* (a) OB5 parsed the SA's synthetic test
   label's pharmacy header as the drug name (mechanism worked end-to-end: suggestions →
   confirm → persist; real-label parsing was verified in Phases 2–3 with METFORMIN);
   (b) EducationPage's static FAQ mis-describes amber as "matches but isn't scheduled for
   this time of day" — amber means abstain; logged for Muthu's FAQ decision (see ADR
   2026-07-19 UX batch entry).

---

## Standing risks

- **IMB1 latency** (Paddle subprocess per call): keep HTTP timeouts ≥180s, UX progress states.
- **SB2 snapshot is demo-grade** — request a refreshed `ca_appearance_harmonized_v2.xlsx`
  from Muthu before any real-use claim (rolling PillImprintValidator adjudication).
- **BB3 store is multi-GB** (SQLite + float32 memmap) — never copy into the repo or an image.
- **Ollama vs GPU contention** — the CB4-first design makes ollama optional; only the offline
  fallback needs it.
- **Frozen dev-set numbers** (verify 31.1%, FA 1.25%) are development-set diagnostics —
  NB08 is the confirmatory campaign; never quote them as generalization guarantees in app copy.
