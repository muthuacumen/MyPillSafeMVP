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
| 5 | UI overhaul: PathoIntern design system + logo + public content chain + assistant chatbot + mobile/PWA | 🟡 PREP DONE — SA assets shipped, build NOT started (run `phase5_builder_prompt.md`) | 2026-07-18 |
| 6 | Packaging, docs, end-to-end verification | ⬜ | |

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
- `documentation/integration/phase5_builder_prompt.md` — the COMPLETE builder prompt +
  next-session resume steps (incl. Muthu's Journey.md-harvest directive: SA lifts intro-worthy
  material from `D:\Projects\PillSafe\Journey.md` into pack §1/§2 BEFORE spawning).

**Build status:** NOT started — a Sonnet build was spawned then stopped within seconds
(Muthu's token budget; no builder files written). Next session: follow the resume steps at the
top of `phase5_builder_prompt.md`.

**Verification bar:** backend pytest fully green (was 93; + new assistant tests incl. zones,
med-redirect, rate-limit 429, voice) · `npm run type-check` + `build` clean · PWA manifest +
SW in build output, installability check · live smoke: real CB4 `/assistant/chat`, med-intent
redirect, clarification + fallback zones, `/assistant/voice` with a generated WAV · decision
tokens diff-clean vs HEAD · SA browser click-through at 360/1280px (landing, all 5 about
pages, widget flows, PillResultPanel states unchanged).

**Result:** _(fill in at completion)_

---

## Phase 6 — Packaging, docs, end-to-end verification

**Goal:** reproducible run story + honest docs.

**Build:** brains sidecar joins the run story (docker-compose extra-host pointing at the
host-run sidecar — GPU stays on host; document why it's not containerized), `Makefile`
targets, README rewrite (architecture diagram now five-brain-accurate, setup steps, feature
flags), `.env.example` refresh, Journey.md gets an integration chapter (SA writes, not
Sonnet), final full-stack E2E: register → scan Rx → confirm DINs → scan pill (verify + reject
+ abstain) → ask Q&A (CB4) → records — on desktop AND a phone-sized viewport.
**Verification bar:** all suites green (app, SB2 8/8, BB3 29/29 in sidecar venv); the E2E
script above executed and logged in this doc.

**Result:** _(fill in at completion)_

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
