# E2E Testing Findings — live site, 2026-07-30

Full record of the DEPLOY_GUIDE **§10 end-to-end verification** run against
`https://mypillsafe.ca` on 2026-07-30. This file is the fix backlog: each finding has
evidence, a location, and a proposed fix with its verification bar.

**Environment under test**

| Thing | Value |
|---|---|
| Site | `https://mypillsafe.ca` |
| Image tag | `20260730-1020` (backend + frontend, both `(healthy)`) |
| Frontend bundle | `index-YDO8h4xA.js` |
| Commit | `1019a4f` on `main` |
| Sidecar | `100.119.95.105:8100`, all brains green (7,055 appearance / 11,609 profile rows) |
| Account | fresh registration, empty profile at start |
| Prep | service worker unregistered + `workbox-precache-v2` deleted before testing |

**Test artefacts** — `D:\Projects\PillSafe\data\eval\`

| File | Content |
|---|---|
| `prescription1.jpg` | Real-style pharmacy label — MANITOBA Pharmacy, APO-AMOXI 500MG / AMOXICILLIN 500MG, "TAKE 1 CAPSULE THREE TIMES DAILY", patient "Toba Man", appearance `RED/YEL/ELLIP/APO{500}` |
| `Prescription2.png` | Fictional 8-medication sheet (Gravol, Senokot.S, Dulcolax, Tylenol ES, Advil, Benadryl, Pharmasave Muscle & Back Pain, Aspirin) |
| `Prescription3.png` | Fictional 7-medication sheet (Motrin, Pharmasave Diarrhea Relief, Pepcid, Benylin Day, Benylin Night, Pharmasave Naproxen, Allergy Remedy) |
| `Prescription2.pdf` | Same as PNG — **could not be uploaded**, see F4 |
| `Pill1.jpg` | Orange round tablet, plain surface, **no capture card** — ground truth **Gravol** |
| `Pill2.jpg` | Small brown/tan round tablet, no capture card — ground truth **Senokot S** |

---

## 1. Schema outage — CLOSED

The 2026-07-30 Postgres schema-drift outage is confirmed resolved, proven three
independent ways rather than by introspection alone.

1. **Droplet schema parity** — `SCHEMA PARITY: OK`, all four tables `ok`.
2. **Live authenticated read** — `GET /api/v1/prescriptions/me` → **200** (the endpoint
   that was returning 500 for My Medications *and* the reminder poll).
3. **Live write** — a prescription created through the UI persisted with **all four
   formerly-missing columns populated**:
   ```json
   {"din":"02401509","review":"approved","src":"qwen",
    "flags":["not_in_reference"],"pv":true,"freq":"TID"}
   ```
   Before the fix this INSERT raised `UndefinedColumn`, so the row could not exist.

Supporting evidence:

- Reminder poll issues `GET /api/v1/prescriptions/me?review_status=approved` → **200**,
  i.e. it filters on the exact column that had been missing.
- Grandfathering correct with no overlap: `approved` rows `2026-07-27 16:12→16:18`,
  `pending` rows `2026-07-30 15:10→15:12`.
- `UndefinedColumn` / `does not exist` count in 4 h of backend logs: **0**.
- `20260730-1020` independently confirmed live by the Vision copy fix
  ("Across Canada, …") and the new bundle hash.

**No action required.**

---

## 2. §10 check results

| # | Check | Result |
|---|---|---|
| 1 | Landing + 5 About pages + 5 brain pages | ✅ PASS |
| 2 | Register → login; wrong password inline error | ✅ PASS (run by Muthu) |
| 3 | Rx scan with a real label photo | ⚠️ **DEFECT — F5** |
| 4 | DIN suggestions → confirm | ✅ PASS |
| 5 | Pill scan, correct pill → `verify` green | ⏸ **NOT RUN** |
| 6 | Pill scan, wrong pill → `reject` red | ✅ PASS (×2) |
| 7 | Pill scan, ambiguous → `abstain` **amber** | ✅ PASS |
| 8 | Celecoxib / sulfa polarity probe | ✅ PASS |
| 9 | Q&A in French | ✅ PASS |
| 10 | PWA install | ✅ PASS |
| 11 | Mobile 360 px | ✅ PASS (verified by Muthu on a real phone) |
| 12 | Disclaimers on every result surface | ✅ PASS |
| §10.1 | Degradation with sidecar down | ✅ CHECKPOINT 15 — with **F2** |
| §10.2 | Resource check (`docker stats`, `free -h`) | ⏸ **NOT RUN** — droplet-side |

**Check 5 is NOT RUN, not passed.** No scan in this session produced a `verify`, so the
green path is unexercised. It must not be recorded as green.

### Check 1 detail — public content is correct

Every red-team correction is live in the deployed bundle: worst-run Rx table
(94/130·2, 120/130·0, **125/130·1†**, 130/130·0) with the three-runs note and G6
footnote; Haiku labelled "not used for prescription reading"; `$0.49` metered with the
workbook pointer; GO-PILL **2026**; MedSnap as "Commercial prior art (~2013)"; CIHI
vintages 2021/2016; 33× scoped to "one common blood thinner"; 8-of-40 vs 0-of-55;
6,803 + 27 monographs / 3.9 M passages; 11,609 vs 7,055 vs 4,554 split; privacy card on
the Answer Voice page.

### Check 4 detail — DIN pipeline verified in production

Typing `amoxicillin 500mg` reached the sidecar as `q=amoxicillin` (`clean_search_query`
stripped the strength) and `_rerank_by_strength` returned **AMOXICILLIN 500 MG ·
DIN 02401509 at rank 1**, above the strength-less candidates. Confirming persisted
("Linked to DIN 02401509") and survived Approve.

### Checks 6 & 7 detail — pill scans

| Scan | Ground truth | Profile at scan time | Outcome | Correct? |
|---|---|---|---|---|
| Pill1 | Gravol | amoxicillin only | reject | ✅ |
| Pill2 | Senokot S | amoxicillin only | reject | ✅ |
| Pill1 | Gravol | + Gravol + Senokot | **reject** | ❌ false reject (F7) |
| Pill2 | Senokot S | + Gravol + Senokot | **abstain** — *"We're not fully certain — is it one of these?"* listing **SENOKOT S first**, then Gravol, then amoxicillin | ✅ |

**Zero false accepts across all four scans.** Both photos were off-protocol (no capture
card, so colour has no white-balance patches); the system flagged "possible shadow
interference" on every one.

### Checks 8 & 9 detail — Q&A polarity

- EN: *"**No.** According to the product monographs, celecoxib should not be given to
  patients with allergies to sulfonamides. This is listed as a contraindication…"* —
  cited DINs 2424371, 2436299, 2429675, 2426382, 2479745; badged `claude-haiku-4-5`.
- FR: *"**Non.** … le celecoxib ne doit **PAS** être donné aux patients allergiques aux
  sulfamides…"* — 5 DINs, polarity preserved through translation.
- Per the corrected §10 check 8, DIN 2239942 was **not** required and did not appear —
  confirming why that criterion was rewritten.

---

## FINDINGS

Ordered by severity.

### F1 — G6 as-needed detection misses "if needed" 🔴 SAFETY

**The most important finding of the session.**

G6 reads as-needed status from the label text and suppresses derived reminder times. It
matches the literal phrase **"as needed"** but **not "if needed"** — semantically
identical, and common on real labels.

Across two labels, 15 medications, the split is perfectly clean and deterministic:

| Label phrasing | Medications | G6 fires? | Times set |
|---|---|---|---|
| "**as needed** every 6 hours" | Dulcolax, Pharmasave Muscle & Back Pain, Pepcid, Allergy Remedy | ✅ 4/4 | none (correct) |
| "after lunch **if needed**" | Gravol, Advil, Motrin, Benylin Cold & Sinus **Night** | ❌ 0/4 | **08:00, 13:00, 18:00** |

Observed values (from the live review screen DOM):

```
Gravol            freq=WITH_MEALS      times=[08:00,13:00,18:00]  asNeeded=false   ❌
Dulcolax          freq=EVERY_N_HOURS   times=[]                   asNeeded=true    ✅
Advil             freq=WITH_MEALS      times=[08:00,13:00,18:00]  asNeeded=false   ❌
Motrin            freq=WITH_MEALS      times=[08:00,13:00,18:00]  asNeeded=false   ❌
Pepcid            freq=PRN             times=[]                   asNeeded=true    ✅
Benylin Night     freq=WITH_MEALS      times=[08:00,13:00,18:00]  asNeeded=false   ❌
Allergy Remedy    freq=PRN             times=[]                   asNeeded=true    ✅
```

**Why it matters.** The project's own safety-event taxonomy counts "setting reminder
times on a medication meant to be taken only as needed" as a safety event. This label
produces **2 safety events**, on the shipped path the public Rx page reports as **post-fix
zero**. The 24-label in-house evaluation set evidently never used the phrase "if needed",
so the gate was never exercised against it.

Most vivid case: **Benylin Cold & Sinus Night** — a night-time sedating product — was
given 08:00 and 13:00 reminders.

- **Where:** `dev/backend/app/services/rx_guardrails.py`, the G6 as-needed matcher.
- **Fix:** extend the lexicon beyond `as needed` — at minimum `if needed`, `if required`,
  `when needed`, `when required`, `as required`, `p.r.n.`, `prn`, plus FR equivalents
  (`au besoin`, `si nécessaire`, `si besoin`). Match on a normalised window, same
  window-scoping and whole-text fallback G6 already uses.
- **Verification bar:** add the two fictional labels to
  `documentation/evaluation/rx_parsing/` as new cases; assert 0 safety events on both.
  Mutation-test it: removing `if needed` from the lexicon must fail the new tests.
  Because qwen is unstable across model loads, prove the guard with **injected-input unit
  tests** (feed the proposal + label text directly), not by re-running the model.

### F2 — Q&A sidecar-down message leaks internal infrastructure 🟠

With the sidecar stopped, the Q&A surface renders to the end user:

> "The brains sidecar service could not be reached. Make sure it is running at
> **http://100.119.95.105:8100**."

Two problems:

1. **Fails §10.1's criterion** ("clear service-unavailable message"). The target user is a
   senior or someone with a language barrier; "make sure the brains sidecar service is
   running" is not actionable for them.
2. **Discloses internal network topology** — the laptop's private Tailscale IP and port —
   to any authenticated user.

The correct copy already exists on the other two surfaces, so this is a copy defect, not a
missing capability:

> "Scanning is temporarily unavailable — the analysis service can't be reached. Your photo
> was fine; please try again in a few minutes." + **Try Again**

- **Fix:** replace the raw error with the same user-facing string (EN + FR, keeping
  `check:i18n` key parity). Never render backend exception text containing a URL or host.
- **Verification bar:** stop the sidecar, confirm the new copy in both locales, and grep
  the built bundle to prove no tailnet IP is present in any user-facing string.

### F3 — Sidecar became an orphan; the brain-deploy mechanism was inoperative 🟠 (FIXED this session)

The process serving port 8100 (PID 64480, started 00:41:26) had this ancestry:

```
python3.12.exe (64480) ← python.exe (64436) ← (chain ends)
```

No `cmd.exe`, no `svchost.exe`. Task Scheduler did not own it. Consequences:

- `schtasks /end` returned **SUCCESS while killing nothing** — health stayed 200.
- The earlier `Last Result: 1` was `/run` silently no-opping against this orphan.
- **Both halves of the documented DEPLOY_GUIDE §12 restart were therefore dead.** Since
  restarting that task *is* the brain-deploy mechanism, any change to `BB3/`, `IMB1_v0/`,
  `SB2/` or `dev/brains/` would have silently never reached production.

**Repaired:** `Stop-Process` on 64480 **and its `python.exe` parent**, then
`schtasks /run`. New banner `---- sidecar start Thu 07/30/2026 16:48:47.05 ----`, health
all-green, ancestry restored to the correct chain:

```
python3.12.exe (32276) ← python.exe ← cmd.exe ← svchost.exe ← services.exe ← wininit.exe
```

- **Standing lesson:** diagnose sidecar liveness **by process ancestry, not by `schtasks`
  exit codes** — the task can report success while owning nothing. Note
  `Last Result: 267009` (`0x41301`) means "currently running" and is healthy.
- **Doc fix owed:** DEPLOY_GUIDE §12 currently prescribes `/end` then `/run` and a banner
  check. Add the orphan case: if `/end` succeeds but `/health` still answers, kill the
  listening PID and its parent directly, then `/run`, then verify the full ancestry chain.

### F4 — PDF prescriptions cannot be uploaded, with no explanation 🟡

The prescription file input declares `accept="image/*"`, so the OS picker filters PDFs out
entirely. `Prescription2.pdf` could not be selected. E-prescriptions and pharmacy emails
are commonly PDF, so this is a real intake gap, and the user gets **no message** telling
them why their file is not selectable.

- **Options:** (a) accept `application/pdf` and rasterise page 1 before OCR; (b) keep
  images only but state it in the UI ("JPG or PNG — if you have a PDF, screenshot it").
- Option (b) is the cheap, honest short-term fix; (a) is the real one.

### F5 — Parser extracted the patient's name as the medication 🟡

On `prescription1.jpg` the review screen proposed medication name **"TA-OBAMAN"** with
**strength empty**. The label's patient name is "Toba Man"; the true medication is
AMOXICILLIN 500 MG (brand APO-AMOXI).

This is a new variant of the known `prescription_parser.py` real-label heuristics bug
(previously observed picking the *pharmacy* name). Per §10's guidance this does not block a
deploy.

**The guardrails behaved correctly and this is worth recording as a positive:**

- `not_in_reference` fired → "Not found in our medication list"
- "Needs your review" badge shown
- Frequency **Three times a day** and times **08:00 / 13:00 / 18:00** were correct
- Nothing auto-committed; DIN linking offered, never forced

The chain was healthy end-to-end (`/ocr/prescription` 200 → `/rx/extract` 200 →
`/reference/search?q=TA-OBAMAN` 200), so this is a **content** defect, not plumbing.

- **Next step to attribute it:** the sidecar's access-level logs cannot separate "OCR
  misread the line" from "parser selected the wrong line". Replay `prescription1.jpg`
  offline through `/ocr/prescription` and inspect the raw text before blaming either stage.

### F6 — Three UNVERIFIED citations are public and load-bearing 🟡

`/about/science` publishes these with author, venue and figures, while the project
bibliography still marks all three **UNVERIFIED (cited from memory)**:

1. **Yaniv et al., "The NLM Pill Image Recognition Challenge", IEEE AIPR 2016** — "the
   challenge winner achieved only **43% top-5** accuracy". The page itself calls this
   *"the argument in one number"*, and `/about/problem` repeats it.
2. **Zeng, Cao & Zhang, "MobileDeepPill", ACM MobiSys 2017** — described as *"The NLM
   challenge winner"*.
3. **Ling et al., "Few-Shot Pill Recognition", CVPR 2020** — "the CURE dataset".

**Possible internal contradiction:** entry 1 attributes 43% top-5 to "the challenge
winner"; entry 2 says MobileDeepPill *is* the winner — but MobileDeepPill's own published
accuracy is substantially higher than 43%, so the two sentences may not describe the same
measurement.

- **Fix:** verify each against the primary source (`WebSearch`/`WebFetch`). Confirm →
  leave. Cannot confirm → rewrite the copy so nothing rests on an unverified number, and
  reconcile entries 1 and 2. The same numbers must not reach the paper unverified.

### F7 — False reject on an in-profile pill 🟢 informational

With GRAVOL DIN 00013803 in the profile, `Pill1.jpg` (ground truth: Gravol) still returned
**reject**. A miss, not a safety failure — reject is the safe direction, and no false
accept occurred in any scan.

Context that makes this expected rather than alarming: both photos were taken **without the
capture card**, so colour constancy has no white-balance patches; the system flagged
"possible shadow interference" on every scan; and the measured verify rate is 31.1% on
dev-set photos *with* the card, with abstain designed to be the common outcome.

- **Not a bug to fix blind.** If it should be pursued, do it as a card-vs-no-card
  comparison inside NB08 rather than as a threshold tweak — loosening SB2 without
  re-running the LOPO eval is a killed idea.

### F8 — Stale card state after DIN linking 🟢 cosmetic

After correcting the medication name and linking a DIN, the card header still displayed the
original parsed name (**"TA-OBAMAN"**) and the "Not found in our medication list" banner
remained visible, even though "Linked to DIN 02401509" was shown below.

- **Fix:** re-render the header from the edited name; clear the `not_in_reference` notice
  once a DIN is confirmed.

### F9 — Horizontal overflow in the ~640–723 px band 🟢 cosmetic

At a 654 px viewport, `document.documentElement.scrollWidth` = 723. Culprit:

```html
<p class="text-xs text-white/40 sm:ml-auto sm:shrink-0">MyPillSafe · 2026 · …</p>
```

600 px wide, `sm:shrink-0` prevents it shrinking. A decorative circle
(`absolute -right-8 … w-32`) overhangs 8 px and is almost certainly inside an
`overflow-hidden` parent (benign).

**Scope is narrow:** `sm:` applies only at ≥640 px, so this affects small tablets and
split-screen, **not** 360 px — Muthu verified real mobile renders correctly.

- **Fix:** allow wrapping below `md`, or drop `sm:shrink-0` on that credit line.

### F10 — French answer carries an English disclaimer 🟢 observation

A French answer renders with the English per-answer disclaimer ("PillSafe is a
decision-support tool, not medical advice…"), because the selector changes the *answer*
language while the UI locale stays English. Arguably by design — but in the app's own
target scenario (a user who reads French, not English) the one sentence that must land is
the one that does not localise unless the whole UI is switched.

- **Consider:** localise the per-answer disclaimer to the *answer* language, independent of
  UI locale.

---

## 3. Suggested fix order for the next session

| Order | Finding | Why first |
|---|---|---|
| 1 | **F1** G6 "if needed" | Only finding with a patient-safety consequence; small, testable, mutation-provable |
| 2 | **F2** Q&A message | Information disclosure + fails §10.1; copy-only, pattern already exists |
| 3 | **F3** doc fix | §12 must describe the orphan case or the next brain deploy silently fails |
| 4 | **F6** citations | Public claims; must be settled before the paper leans on them |
| 5 | **F4** PDF intake | Real user-facing gap; cheap honest fix available |
| 6 | **F8 / F9 / F10** | Cosmetic / UX polish |
| 7 | **F5** attribution | Needs an offline OCR replay to attribute correctly |
| — | §10.2 + check 5 | Resource check on the droplet; verify path still unexercised |

## 4. Still owed from §10

- **§10.2 resource check** (droplet): `docker stats --no-stream` and `free -h`;
  CHECKPOINT 16 = containers well under `mem_limit`, comfortable free RAM.
- **Check 5 (green verify)** — needs a capture-card photo of a pill that is in the profile.
  Until then it stays NOT RUN.
