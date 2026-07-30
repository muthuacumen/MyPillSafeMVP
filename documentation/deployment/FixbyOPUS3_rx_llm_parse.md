# FixbyOPUS3 — Rx-Parse Redesign: Local qwen2.5:7b Proposer behind Confirm, with Deterministic Guardrails

**Written:** 2026-07-28, by /pillsafe SA (Fable), revising FixbySonnet3 per Muthu's three directives:
(1) **production proposer = qwen2.5:7b** — Haiku's measured superiority is recorded as a FINDING,
not wired as a dependency; (2) a **measured-limitations documentation section** with the three-way
comparison and a published experiment-data folder is part of this build; (3) **the builder is an
OPUS agent** ("FixbyOPUS3") — an explicit, Muthu-authorized exception to the build-on-Sonnet
convention (`feedback_build_verify_opus` stands for other builds). SA verification runs in a
separate session afterward (checklist §10).
**Status:** SPEC, ready to build — no code written yet. **Muthu's calls (2026-07-28, AskUserQuestion):
the OPUS builder spawns in the NEXT session, and Task B (§9) is INCLUDED in this build.**

**AMENDED 2026-07-28 (SA pre-build review, Opus session — four Muthu calls).** Four changes, each
marked ⟦AMENDED⟧ at its section. Two are SA-found defects, two are Muthu's IA/scope calls:
1. **§4 G2 no longer strips `drug_name`/`dosage`** — it normalizes OCR-confusable characters, then
   flags. As originally written G2 would have deleted the *correct* name and dosage on held-out
   case `H10-ocr-noise-atorvastatin` (raw text `AT0RVASTATIN 2O MG`, truth `atorvastatin`/`20mg`) —
   i.e. destroyed value on exactly the labels the LLM was selected to rescue, and likely broken
   §7's own ≥11/12 via-service bar by the guard's own behaviour. `redteam_llm_extraction.py:386,389`
   already carries an `ocr_noise` exemption in its scorer; the guardrail spec had not inherited it.
2. **§8 public placement moves** from a SciencePage anchor to a NEW dedicated
   `/about/brains/prescription-reader` page that explains OB5 itself and carries the limitations
   as a subsection — the first of five per-brain pages Muthu will expand in later sessions.
3. **§0.7 carve-out:** that page ships **English-only**, matching the rest of the public About
   chain (AboutPage/SciencePage contain zero `t()` — only `about.nav.*` is translated). The
   chain-wide FR gap is logged as a tracked item, not fixed here.
4. **§10 verification bar** updated to match 1–3.

---

## 0. Non-negotiables (violating any is a failed build)

1. **Nothing auto-commits a drug name, DIN, or schedule.** Every parsed medication is a PROPOSAL
   until the user approves it in the review screen. Layer 1 (entity → Canadian-DIN scoping) stays
   deterministic (ADR 2026-07-22 layered safety model).
2. **Frozen packages untouched:** `IMB1_v0/`, `SB2/`, `BB3/` — zero file changes, verified by mtime.
3. **Honest failure only.** No parse path may fabricate a medication, dosage, or time. The regex
   fallback's silent `["morning"]/["08:00"]` default is removed from the new path by guardrail G4.
4. **Decision-colour tokens byte-identical**; `PillResultPanel.tsx` zero diff.
5. Allowed paths: `dev/backend/**`, `dev/frontend/**`, `dev/brains/**` (new endpoint only — never
   the frozen sibling packages), `documentation/**`, `.env.example`, `README.md`. `docker/` untouched.
6. Nothing committed; Muthu commits after SA verification.
7. EN/FR i18n lockstep for every new user-visible string — **⟦AMENDED⟧ with one logged carve-out:
   the new `/about/brains/prescription-reader` page (§8) ships ENGLISH-ONLY.** Reason: the entire
   public About chain is hardcoded English (`AboutPage.tsx`/`SciencePage.tsx` have zero `t()`
   calls; only `about.nav.*` exists in `en.json`/`fr.json`), so a translated brain page would drop
   a French reader into French content one click from an English card and back to English after.
   Muthu's call 2026-07-28. **Lockstep still applies in full to every in-app string** (review
   screen, flag chips, badges — Tasks A4 and B3). The About chain's FR gap is a tracked item.
8. **No fabricated statistics anywhere.** The limitations doc reports measured counts
   (counts-not-percentages at small n), names the eval as SA-authored/held-out, and never claims
   "100% accuracy" — the honest form is "12/12 labels, 50/50 fields on this evaluation set."

## 1. Evidence and the model decision (measured 2026-07-28, all re-runnable)

Harness: `redteam_llm_extraction.py` (this folder) → `redteam_llm_extraction_results.json`.
24 labels: the original 12 (regex's own dev fixtures) + 12 held-out realistic Canadian shapes
(weekly, q8h, bare-daily, taper, split-dose, French, sig codes, OCR noise, half-tablet,
insulin/units, unenumerated no-strength multi-med).

| system | orig 12 (home turf) | held-out fully-ok | held-out fields | safety events | mean lat | cost/call |
|---|---|---|---|---|---|---|
| regex parser (current prod) | 12/12 | **1/12** | 25/50 | **2** (daily-reminder-for-WEEKLY med; missed med) | ~0 s | 0 |
| **qwen2.5:7b (local, SELECTED)** | 12/12 | 11/12 | 49/50 | 0 | 7.1 s | 0 |
| claude-haiku-4-5 (finding only) | 12/12 | 12/12 | 50/50 | 0 | 1.45 s | ~0.13¢ |

> **Superseded scoring (noted 2026-07-29, table left as the dated build-time record).** The
> "orig 12" column above is medication-count + name-fragment only, so no frequency, dosage or
> reminder-time error on those 12 labels could register — the "safety events" column is a
> statement about the held-out 12 alone. The original 12 were widened to per-field scoring on
> 2026-07-29 (80 added fields, 130 total) and every arm re-run 3× because qwen at temperature 0
> is measured non-deterministic. Current numbers:
> `documentation/evaluation/rx_parsing/results_*_perfield.json` + README §3. This table is not
> updated on purpose: the movement between the two is the finding.

**Muthu's model decision (2026-07-28, durable): qwen2.5:7b-instruct is the capstone's production
proposer.** Rationale: self-contained local-first posture, zero marginal cost, no new cloud
dependency; the ML tier (Muthu's laptop over Tailscale) already serves production. **Recorded
finding, to be stated in the limitations doc:** Haiku 4.5 measured strictly better (12/12, 50/50,
0 events, 1.45 s); a stronger cloud model is expected to perform at least as well. The
architecture keeps the proposer swappable behind one config value, so upgrading later is a
config change, not a redesign.

**qwen's single measured miss** was NOT frequency extraction — it was the time-slot *derivation*
(mapped BID to 08:00+13:00 instead of 08:00+18:00 on the French label). §2's design therefore
removes time derivation from the LLM entirely, which converts the 7B's one weakness into a
structural non-issue. Guardrail grounding: MEDIC (Nature Medicine 2024, primary-source verified
this session) — catalog cross-check + halt conditions + abstain-over-generate; Agrawal et al.
EMNLP 2022 (few-shot clinical extraction).

## 2. Architecture

```
photo → sidecar OCR (unchanged) → raw_text
  → backend calls sidecar POST /rx/extract {raw_text}        [NEW sidecar endpoint]
       sidecar → local Ollama (127.0.0.1:11434) qwen2.5:7b-instruct
                 temperature 0, num_ctx 8192, format json, keep_alive "10m"
       (1 corrective retry on bad JSON; 60 s cap)
  → on sidecar/Ollama failure or RX_LLM_PARSE_ENABLED=false → regex parse_medications()
  → guardrails.apply(proposals, raw_text)                     [backend, deterministic, BOTH proposers]
  → DERIVE reminder times server-side from frequency_type     [deterministic — never the LLM]
  → Prescription rows persisted with review_status='pending' (additive column)
  → DIN suggestions attached as today (/reference/search)
  → REVIEW SCREEN: user edits/approves each med → review_status='approved'
  → reminders/schedules activate ONLY for approved meds
```

Key properties: the proposer is swappable (config `RX_PARSE_BACKEND=qwen|regex`; a future
`haiku` value is documented, not implemented); guardrails and time derivation are
proposer-agnostic; the LLM lives on the ML tier (sidecar host), never the droplet.

**Ops constraints honored (measured 2026-07-28, in the red-team brief §3):** qwen resident +
live pill analysis peaks 7,374/8,188 MiB with no CPU offload — coexistence fits; `num_ctx` is
ALWAYS passed explicitly (silent-truncation trap); `keep_alive "10m"` releases VRAM when idle
(cold reload 7.5 s is acceptable inside a 15–20 s OCR flow); the standing "no Ollama during GPU
batches" rule means NB08 batch runs pause Rx parsing on the dev box — acceptable, dev-time only.

## 3. Task A1 — sidecar `POST /rx/extract` (`dev/brains/`)

- New route in the sidecar app (same style as `/ocr/prescription`): body `{raw_text}`, returns
  `{medications: [...], model, elapsed_seconds}` or a typed error (backend falls back on any
  non-200 / timeout — honest degradation, never fabrication).
- Calls Ollama via HTTP (urllib/httpx — no new heavy deps): model `qwen2.5:7b-instruct`,
  `temperature 0`, `num_ctx 8192`, `format: "json"`, `keep_alive "10m"`, 60 s timeout, one
  corrective retry on unparseable JSON.
- **Prompt: start from the PROMPT constant in `redteam_llm_extraction.py` and modify ONLY as
  follows** (it produced the measured numbers — do not rewrite the rest): remove the
  slot→time derivation block; `specific_times` becomes `explicit_times` = ONLY clock times
  literally printed on the label ("8:00 PM" → "20:00"), else `[]`; add "output at most 20
  medications". Schema per med: `drug_name, dosage, frequency_type ∈ {ONCE_DAILY, BID, TID, QID,
  BEDTIME, WITH_MEALS, PRN, WEEKLY, EVERY_N_HOURS, TAPER, UNKNOWN}, explicit_times, with_food`.
- `/health` gains `rx_extract: "ok"|"ollama_unreachable"` (non-fatal — pill/Q&A unaffected).

## 4. Task A2 — `app/services/rx_guardrails.py` (backend; MEDIC GR1–GR5 transplanted)

Applied to the proposal list regardless of proposer. Guards set per-field/per-med FLAGS; they
never silently rewrite except where stated:

- **G1 catalog:** each `drug_name` → `/reference/search` (existing failure-tolerant pattern).
  No hit ⇒ flag `not_in_reference` (med still shown — the reference is incomplete until Task B).
  Suggestions attach exactly as Phase 2 does today.
- **G2 no-invention ⟦AMENDED 2026-07-28 — asymmetric: times strip, name/dosage flag⟧.**
  Comparison runs over an **OCR-confusable normalization** of both sides (case/space/punctuation
  fold, then `0↔O`, `1↔l↔I`, `5↔S`, `8↔B`, `rn→m`, `2↔Z`), so `AT0RVASTATIN 2O MG` matches
  `atorvastatin` / `20mg`. Beyond that fold, name matching uses a similarity threshold
  (best-matching raw-text token, `difflib.SequenceMatcher` ratio ≥ 0.85 — stdlib, no new dep)
  rather than exact containment.
  - `explicit_times`: every entry must correspond to a clock time present in `raw_text`.
    Violation ⇒ **STRIP** to `[]` + flag `not_on_label`. Safe by construction — G4's deterministic
    derivation then supplies the reminder times from `frequency_type`.
  - `dosage` and `drug_name`: violation after normalization + threshold ⇒ **KEEP the value, do NOT
    null it**, + flag `not_on_label`. The field renders amber and unconfirmed in the review screen,
    and **the med cannot be approved until the user explicitly edits or confirms that field**
    (A4 enforces this — same gate `needs_schedule` uses).
  - Rationale: nothing auto-commits (§0.1), so the protection was always the human confirm, never
    the deletion. Stripping hands a tired senior a blank to retype off a label they may not read
    well, and deletes the LLM's OCR-repair value. This is also the more MEDIC-faithful reading —
    MEDIC's guardrails *flag for pharmacist review*; its 95.1% is a flagging metric, not a
    deletion metric.
  - Test obligation (adds to §7): a unit proving H10-class text yields a KEPT `atorvastatin`/`20mg`
    (flagged or clean), and a unit proving a genuinely invented dosage absent from raw text is
    flagged `not_on_label` and blocks approval until touched.
- **G3 schema:** frequency outside the enum ⇒ `UNKNOWN`; malformed times dropped.
- **G4 no-silent-defaults + deterministic time derivation:** reminder times are computed
  server-side: explicit_times (G2-verified) win; else map frequency via the canonical table
  (ONCE_DAILY→[08:00], BID→[08:00,18:00], TID→[08:00,13:00,18:00], QID→[+21:00],
  BEDTIME→[21:00], WITH_MEALS→[08:00,13:00,18:00]); **PRN | WEEKLY | EVERY_N_HOURS | TAPER |
  UNKNOWN ⇒ [] + flag `needs_schedule`** — the review screen forces the user to set the schedule;
  the app NEVER invents 08:00. The regex fallback's default-morning is stripped on this path.
- **G5 conflict:** >1 distinct dosage for one med, or duplicate `drug_name` proposals ⇒ flag
  `conflict` (both shown, user resolves).

## 5. Task A3 — wiring + persistence (backend)

- `routes/prescriptions.py`: parse stage becomes sidecar-extract → guardrails → derive-times;
  regex fallback on failure. Response gains per-med `parse_source ∈ {qwen, regex}` + `flags`.
- Additive `Prescription` columns via the boot-time column sync: `review_status` (String(16),
  default `'pending'`), `parse_source` (String(16)), `parse_flags` (String(255)).
  Pre-existing rows grandfather to `'approved'` (document this).
- `PATCH /prescriptions/{id}`: accepts edited fields + `review_status='approved'` (tri-state
  handling like `din_confirmed`). Any edit keeps status pending until explicit approve.
- Reminder/schedule surfaces filter to `review_status='approved'`.
- Config: `RX_LLM_PARSE_ENABLED` (default true; false ⇒ regex proposer — guardrails + derivation
  STILL apply), `RX_PARSE_BACKEND` (default `qwen`). `.env.example` updated. sha256-style log
  line per parse (source, flags, elapsed) — same pattern as the Task-1d OCR anomaly log.

## 6. Task A4 — review/edit/approve screen (frontend)

- After Rx-scan and on MyMedications: pending meds render in a **"Review your medications"**
  panel — per med: editable name/dosage/frequency/times/with_food, flag chips
  (`not_in_reference`, `not_on_label`, `needs_schedule`, `conflict`), the existing `DinLinkPanel`
  for DIN confirm, an explicit **Approve** button. Amber styling for pending (pending is never
  success-green). A `needs_schedule` med cannot be approved until a frequency/time is chosen
  (defaults shown as *choices*, never prefilled facts). Disclaimer pinned; EN/FR; fits 360 px.

## 7. Task A5 — tests

- Guardrail units: all five guards; weekly/PRN ⇒ no times; explicit-time-not-on-label strip;
  regex-default-morning strip; conflict duplicate; **derivation unit proving the H7 class is
  impossible by construction** (freq BID ⇒ exactly [08:00,18:00], never the LLM's numbers).
- Sidecar endpoint tests with mocked Ollama (good JSON / malformed-then-good / down ⇒ typed error).
- Backend service tests: sidecar-down ⇒ regex fallback with `parse_source='regex'`; route tests:
  pending-by-default, approve flow, reminders filtered to approved.
- Baseline: full backend suite (127 at spec time) stays green; frontend `tsc` + `vite build`.
- **Acceptance (pre-registered):** add `--via-service` mode to `redteam_llm_extraction.py`
  routing the same 24 labels through the real sidecar+guardrails+derivation path. Bar:
  held-out fully-ok **≥ 11/12**, safety events **0**, zero meds persisted with times for
  WEEKLY/PRN, and the derivation test shows H7 now scores times correctly (expected 12/12).

## 8. Task A6 — measured-limitations section + published experiment folder

**Recommended section/folder title: "Prescription Scanning: Measured Limitations"** (the SA's
proposal replacing "OCR Limitations" — the measured layer is parsing of OCR text, and the section
covers both layers; alternates if Muthu prefers: "Reading the Label: What We Measured" /
"Label-to-Profile: Known Limits"). Muthu picks the final name at review; builder uses the
recommendation meanwhile.

- New folder **`documentation/evaluation/rx_parsing/`** containing ALL experiment data:
  - `README.md` — the limitations write-up: (a) OCR layer limits (real-label misparse history,
    garbled-text incident, CPU OCR latency); (b) parsing layer: the §1 three-system table
    verbatim, counts not percentages, dev-set caveats stated (SA-authored held-out set, single
    run, temperature 0); (c) **the model finding, stated honestly:** "Claude Haiku 4.5 measured
    12/12 labels fully correct (50/50 fields, 0 safety events) on this evaluation; a more
    powerful cloud LLM is expected to perform at least as well. The capstone deliberately selects
    the local qwen2.5:7b for self-containment and zero cloud cost; the proposer is swappable by
    config."; (d) reference-coverage limit: 11,609 marketed human DINs vs the 7,055 oral-solid
    tier (39% of marketed meds not DIN-linkable until Task B); (e) citations (MEDIC w/ DOI,
    Agrawal EMNLP 2022, MedEx JAMIA 2010).
  - `labels_and_ground_truth.json` — exported from the harness (24 labels + truths).
  - `results_three_way.json` — copy of `redteam_llm_extraction_results.json`.
  - `harness_pointer.md` — how to re-run (`redteam_llm_extraction.py`, env prerequisites).
- Root `README.md` gains a short "Measured Limitations" link to the folder.
- **Public placement ⟦AMENDED 2026-07-28 — a dedicated brain page, not a SciencePage anchor⟧.**
  Muthu's call: the "Prescription Reader (OCR)" card in AboutPage's "The Five Brains" section
  links to a **NEW page that explains the Prescription Reader itself**, with the measured
  limitations as a subsection inside it. This is **the first of five per-brain pages** — Muthu
  will expand the other four (Pill Vision, Deterministic Matcher, Monograph Q&A, Cloud Voice) in
  later sessions, so build it as a reusable template, not a one-off.
  - **Route: `/about/brains/prescription-reader`** → `pages/public/brains/PrescriptionReaderPage.tsx`.
  - **Do NOT add it to `ABOUT_PAGES`** (`components/AboutNav.tsx`). That array is the single
    source of truth for the linear About chain AND is consumed by `Navbar.tsx` and
    `AppFooter.tsx`; five brain pages would turn a 5-step narrative into a 10-step one and bloat
    the nav. Brain pages are **off-chain detail pages** (same status as Contact), each with a
    "← Back to About" link. `SciencePage.tsx` is **not touched at all**.
  - **Page structure (the template):** (1) hero — brain name, icon reused from `FIVE_BRAINS`, the
    one-line role; (2) "What it does" — plain-language, senior-readable; (3) "How it works" — the
    OCR → parse → guardrails → *you confirm* chain, emphasising that nothing is auto-committed;
    (4) **`<section id="rx-limitations">` "Prescription Scanning: Measured Limitations"** carrying
    the same honest framing as the repo doc: the three-system table with counts-not-percentages,
    the held-out-eval caveat sentence, the Haiku finding worded exactly as §8(c), the
    coverage-limit sentence, and a note that the full experiment data ships in the repository
    (`documentation/evaluation/rx_parsing/`) — no external GitHub link (the repo is private; a
    dead link is worse than a note); (5) back-to-About link.
  - Card link text: "Learn more →" on the card (the page covers the brain, not only its limits).
  - **English-only per the §0.7 carve-out.** Match the surrounding hardcoded-copy convention of
    `AboutPage.tsx`; do not add `about.brains.*` keys to the locale files.
  - Table must be readable at 360 px without horizontal page scroll — wrap it in its own
    `overflow-x:auto` container.
- **Standing-rule carve-out (logged in the ADR):** the no-dev-set-metrics-on-public-pages rule
  stays in force for IMB1/SB2/BB3 performance numbers; this Rx-parsing limitations disclosure is
  a Muthu-authorized exception — honest-limitations content, not a performance claim. Do not
  touch any other public copy.

## 9. Task B (INCLUDED — Muthu's go, 2026-07-28) — two-tier profile reference

Measured: Human∩Marketed = **11,609 DINs** (DPD snapshot `data/Pills_Patient_Access_Canada.xlsx`);
appearance scope = 7,055. 4,554 marketed human medicines (39%) currently cannot be DIN-linked.
- B1: `dev/brains/data/profile_reference_v1.csv` (11,609 rows: din, brand, company, ingredients,
  forms, routes, schedules) generated by a documented script from the DPD snapshot (provenance +
  refresh path noted; Muthu owns refreshes).
- B2: sidecar `/reference/search` searches the 11,609 tier; response adds `pill_verifiable: bool`
  (din ∈ 7,055). Appearance tier and everything SB2 consumes UNCHANGED.
- B3: frontend badge on confirmed non-oral-solid meds: "Not pill-verifiable — this medication
  type can't be checked by photo" (EN/FR); pill-scan profile DIN list still draws only from
  pill-verifiable confirmed DINs.
- B4: BB3 unaffected (honest not-found refusal); note only.

## 10. SA verification bar (next session, independent re-run)

Suites re-run; diff-scope audit (§0.5 paths; frozen packages mtime); live probes: weekly label ⇒
no reminder before approval; French label ⇒ both doses via derivation; Ollama stopped ⇒
`parse_source='regex'` + functional app + honest health; `--via-service` acceptance reproduced;
browser click-through of the review screen desktop + 360, EN/FR; decision-token freeze;
fabricated-claims grep over ALL new copy incl. the limitations doc (counts only, no "100%");
limitations folder complete + README link; **⟦AMENDED⟧ public placement live: AboutPage Five
Brains "Prescription Reader (OCR)" card → `/about/brains/prescription-reader` renders, the
`#rx-limitations` section is present, `ABOUT_PAGES`/Navbar/AppFooter show NO new chain entry,
`SciencePage.tsx` diff is empty, back-to-About works (desktop + 360, no horizontal scroll, table
readable at 360; English-only is expected here — check FR only for the in-app A4/B3 strings)**;
**⟦AMENDED⟧ G2 asymmetry proven live: an H10-class noisy label keeps its name+dosage (not
nulled), an invented dosage is flagged and blocks approval until touched**; Task B: 11,609 search
live, Lantus-class DIN-links, `pill_verifiable=false` badge, one SB2 pill-verify E2E regression.

**Verification hygiene (standing):** clear the service worker + caches before ANY browser
click-through (`sw-stale-bundle-verification-trap`) — a stale precache has already faked one
failure against correct code.

## 11. Out of scope

BB3 Finding #5 (next work package); real pharmacy label acquisition; Haiku wiring (documented
finding only); multi-language OCR; prod redeploy (after this + Finding #5 per DEPLOY_GUIDE §4/§7).

---

# Builder Report (2026-07-28)

**Builder:** OPUS agent, spawned per §Status. **It terminated early on an API session limit**,
having completed Tasks A1–A6 and B1–B4 and run the acceptance bar, but before writing this
report. The SA finished the remainder inline on Opus — the same documented exception taken when
the FixbySonnet2 builder died mid-run (ADR 2026-07-28): the remainder was small, fully specified,
and re-spawning a cold agent would have re-derived context at higher cost. **SA-authored portions
are marked ⟨SA⟩** so the next session's independent verification knows exactly what was not
written by the builder. Everything below is measured, with the command output behind it.

## Acceptance bar (§7, pre-registered) — **MET**

`redteam_llm_extraction.py --via-service`, 24 labels through the real sidecar + guardrails +
deterministic derivation → `redteam_llm_extraction_via_service_results.json`:

| metric | bar | measured |
|---|---|---|
| original 12 fully-ok | (not barred) | **12/12**, 0 phantom |
| held-out fully-ok | ≥ 11/12 | **11/12** |
| held-out fields | — | **49/50** |
| **safety events** | **0** | **0** |
| WEEKLY/PRN persisted with times | 0 | **0** (`weekly_or_prn_with_times: []`) |
| parse sources seen | qwen | `["qwen"]` |
| latency | — | mean 2.72 s, max 9.5 s |

**The bar passed, but the spec's *expectation* of 12/12 did not materialise.** §7 predicted
deterministic derivation would lift qwen to 12/12. It fixed the case it was designed to fix (H7
French BID now scores correctly — the whole reason derivation moved server-side) but a different
case, **H6, remains imperfect. Reported rather than smoothed over.**

### The one held-out miss: H6-split-dose-morning-bedtime

Label: `Take 1 tablet in the morning and 2 tablets at bedtime with food`. Truth times
`["08:00","21:00"]`. qwen returns `frequency_type: BEDTIME`; derivation yields `["21:00"]`.
**The morning dose is lost.** Name, dosage and frequency-enum all scored OK (3/4 fields); no
safety event fired, because the harness's event taxonomy covers PRN/weekly/not-on-label, not
dropped doses.

Root cause is **the frequency enum, not the model**: §3's enum has no category for asymmetric
split dosing ("1 tab AM, 2 tabs PM"), so no available value is correct — `BID` would give
`[08:00,18:00]`, also wrong (bedtime ≠ 18:00). This exact shape is already on the ADR's
not-fixed list from the 2026-07-28 leftovers entry ("tapers and `1 tab AM, 2 tabs PM`"), so it is
a **pre-existing known gap now measured under the new architecture**, not a regression.

⟨SA⟩ **Design note for the next work package, deliberately NOT built here:** the honest fix is
not a new enum value but routing split-dose labels to `needs_schedule` so the review screen makes
the user set both times. That is a behaviour change to G4 and belongs in its own scoped change
with its own tests — adding it here would have been unrequested scope on top of an already-large
build. Flagged, not silently absorbed.

## What was built, per task

| task | status | key artifacts |
|---|---|---|
| A1 sidecar `POST /rx/extract` | done | `dev/brains/rx_extract.py`, route + `/health` field in `dev/brains/app.py` |
| A2 guardrails G1–G5 | done | `dev/backend/app/services/rx_guardrails.py` |
| A3 wiring + persistence | done | `rx_extract_service.py`, `routes/prescriptions.py`, `models/prescription.py`, `core/database.py` |
| A4 review/edit/approve screen | done | `components/MedicationReviewCard.tsx`, MyMedications integration |
| A5 tests | done | `test_rx_guardrails.py`, `test_rx_extract_sidecar.py`, `test_rx_review_flow.py` |
| A6 limitations doc + experiment folder | done | `documentation/evaluation/rx_parsing/` (5 files), root `README.md` §10, `pages/public/brains/PrescriptionReaderPage.tsx`, `content/fiveBrains.ts` |
| B1 profile reference | done | `dev/brains/scripts/build_profile_reference.py` → `dev/brains/data/profile_reference_v1.csv` |
| B2 two-tier `/reference/search` | done | `dev/brains/app.py` |
| B3 `pill_verifiable` badge | done | `MyMedicationsPage.tsx`, `types/index.ts` |
| B4 BB3 note-only | done | no BB3 change (correct — frozen) |

### §4 G2 amendment — implemented as amended, not as originally spec'd

`NAME_SIMILARITY_THRESHOLD = 0.85` + `_CONFUSABLE` translation table + `rn`→`m` fold;
`difflib.SequenceMatcher` (stdlib, no new dependency). Asymmetry is real in code and in tests:
`test_g2_keeps_name_and_dosage_on_an_ocr_noise_label` (the H10 case that motivated the
amendment), `test_g2_keeps_but_flags_an_invented_dosage_and_that_flag_blocks_approval`,
`test_g2_strips_a_time_that_is_not_printed_on_the_label`. The builder added a test the spec did
not ask for and should have — `test_confusable_fold_does_not_collapse_genuinely_different_drugs`
— which guards the fold's own risk of over-collapsing distinct drug names. Also present:
`test_g4_makes_the_h7_failure_class_impossible_by_construction` (§7's explicit obligation) and
`test_both_proposers_land_on_identical_guarded_output_for_the_same_label` (proves guardrails are
proposer-agnostic, an §2 architectural claim).

### Task B1 lineage — the stop-condition reproduced exactly

`profile_reference_v1.csv`: **11,609 rows, 11,609 unique DINs, 7,055 with `pill_verifiable=true`**
— matches the measured DPD figures exactly, confirming lineage.

**Live proof B1+B2 close the 39% gap** (⟨SA⟩ probe against the running sidecar):
`GET /reference/search?q=lantus` → three LANTUS DINs, each `"pill_verifiable": false`. Insulin was
previously un-DIN-linkable; it now resolves in the profile tier and is correctly marked as not
photo-verifiable.

## ⟨SA⟩ Defect found and fixed while finishing: `pill_verifiable` was dead at three layers

The sidecar returned `pill_verifiable` (B2) and the frontend type already declared it on the
search-result shape (`types/index.ts:109`), but **`brains_client.search_reference` rebuilt its
result dict from only `din/product/strength/score`, and `DinSuggestion` (the route's
`response_model`) had no such field** — so it would have been stripped even if the client had
passed it. The field was silently always `undefined` in the search box.

This did not break Task B3 as spec'd (that badge renders on *confirmed* meds, which flow through
`routes/prescriptions.py:284` and did carry the flag). It was a latent bug: a declared-but-never-
populated field that renders as "not verifiable" the moment someone binds to it.

Fixed minimally — passthrough in `brains_client.py`, field added to `DinSuggestion` — with the
degradation direction made explicit: **a missing flag is `None` (unknown), never `False`**,
because "we could not ask the sidecar" must not render to a senior as "this medication cannot be
checked by photo". Two regression tests added in `test_reference.py`
(`..._carries_pill_verifiable_both_ways`, `..._missing_flag_is_unknown_not_false`).

## Suites (⟨SA⟩ re-run, repo venv `dev/backend/venv`)

- **Backend: 186 passed, 0 failed** (127 baseline → 184 from the builder → **186** with the two
  SA regression tests). 29.3 s.
- **Frontend: `tsc --noEmit` clean (exit 0); `vite build` clean**, PWA precache **67 entries /
  3298.68 KiB** (was 64 / 3275.25 — consistent with the new lazy-loaded brain page).
- **Frozen packages `IMB1_v0/`, `SB2/`, `BB3/`: clean by mtime** (no file modified since
  09:00 today). Checked by mtime, not `git status` — they are not git repos and a naive status
  walks up to the `D:\Projects` parent, a false alarm logged previously.
- `SciencePage.tsx`: **zero diff**, as required by the §8 amendment.
- `ABOUT_PAGES` still has **5 entries** — the brain page is correctly off-chain.
- `.env.example`: `RX_LLM_PARSE_ENABLED=true`, `RX_PARSE_BACKEND=qwen` present.

## Environment at report time

Ollama serving `qwen2.5:7b-instruct`, 100% GPU, **context 8192** (the explicit `num_ctx` the ops
rule demands — confirmed live, not assumed), `keep_alive` honoured. Sidecar listening on 8100.

## Not done / carried

- **This report's ⟨SA⟩ portions were not builder-verified** — the next session's independent SA
  verification should treat them with the same scrutiny as the rest.
- **§10's live browser click-through was NOT performed** (review screen desktop + 360, EN/FR,
  brain-page anchor, decision-token freeze, fabricated-claims grep over the new public copy).
  That is the next session's job, and it must clear the service worker + caches first
  (`sw-stale-bundle-verification-trap`) — a stale precache has already faked one failure here.
- H6 split-dose (above) — design note recorded, not built.
- Nothing committed. HEAD remains `115f8ba`; the working tree is FixbySonnet1 + FixbySonnet2 +
  leftovers + this build, awaiting one combined commit after verification.
