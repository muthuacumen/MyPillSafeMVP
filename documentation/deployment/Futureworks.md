# Futureworks — the parked-risk register

**Audience: someone deploying or operating mypillsafe.ca who is NOT deep in `NB08_Notebook/`.**
This file lists every known risk this project has **deliberately parked** — not fixed, not
disproven, set aside on purpose, with a reason. It does not restate active roadmap work; those
items get a one-line pointer to where the live version lives, never a copy, because a duplicate
roadmap is the exact failure the source project's anti-clutter discipline exists to prevent.

**Format per entry:** the risk · current status · why parked · what would unpark it · the owning
doc.

---

## 🔴 THE ROADBLOCK PROTOCOL (Muthu, 2026-08-12 — binding on every session and every subagent)

**When a step hits something it cannot resolve, it does NOT resolve it silently and it does NOT
stop the bundle.** It parks the risk here and continues with everything not downstream of it.

Every parked roadblock carries **four fields**:

1. **What was hit** — the finding, with the number, and the doc that owns the evidence.
2. **What it blocks** — which roadmap step or which claim cannot proceed.
3. 🔴 **THE ASK** — written as a concrete action **for Muthu**, not as a recommendation the SA acts
   on. Configuration and scope are Muthu's; evidence and the ask are the SA's.
4. **Owning doc** — where the full detail lives. Never restate the numbers here.

**Worked example, given by Muthu when he set this rule:** if the roadmap-1.4 corroboration cap turns
out to make `dulcolax` unverifiable on the happy path, the SA does **not** edit the allowlist. It
parks an entry whose ask reads *"remove `dulcolax` from `data/allowlist/supported_dins.csv`"* — with
the evidence beside it — and membership stays Muthu's call.

**Why the rule exists:** it keeps the division of labour intact (the SA builds holistically; Muthu
controls which pills qualify) and it stops a blocked step from either stalling the milestone or
being quietly worked around. A roadblock that is parked is visible; a roadblock that is resolved by
the SA's own judgement is not.

**Scope discipline:** this file is for PARKED risks only. If you are looking for what is actively
being worked on, do not read this file for that — follow the pointer in each entry to the live
document instead.

**Provenance:** seeded 2026-08-12 from `IMB1_Prototype/NB08_Notebook/`'s registers (roadmap steps
1.2 and 1.4). Every entry below was checked against its owning document before being written here,
not copied from a summary. Maintained going forward by whoever's session next changes one of these
risks' status — update this file in place, do not create a second one.

---

## 1. Dimensions / surface area

**Risk:** the app does not measure or use physical pill size (diameter/thickness) as an
identification signal, even though a wrong-size pill is an obvious human tell.

**Status:** parked, ungrounded — not merely deferred for lack of time.

**Why parked:** Health Canada's Drug Product Database carries **no dimension field in any
endpoint**, verified directly against the DPD API documentation. Even a perfect on-device
measurement would have nothing to match against for a Canadian DIN — the imaging question never
gets to matter. Every dedicated pill-identification research group has independently declined
size for the same reason (2016 NLM Challenge → MobileDeepPill 2017 → ePillID 2020 → Frontiers
2026; ePillID had access to a size field and chose not to use it). The out-of-plane/thickness
measurement problem also has no answer anywhere in the literature, for pills or any close analogue.

**What would unpark it:** three things would all need to become true — a Canadian dimension data
source, a validated accuracy figure at 5–20 mm under real phone capture, and an ablation showing
size adds anything once imprint/colour/shape are already scored. Nobody has measured that last
gap either way; it is the genuine open question if this is ever revisited.

**Owning doc:** `NB08_Notebook/specs/NB08_DataModel_v3.md` §6.1.

---

## 2. F7 — relief-similarity matching

**Risk:** an alternative imprint-matching signal (image-similarity against a reference relief
gallery) that could pay the imprint score term without ever reading text.

**Status:** dissolved inside `NB08_Notebook/`, 2026-08-08. Survives **outside** `NB08_Notebook/`
as a fallback path only.

**Why parked:** F7 has no corpus story at formulary scale — every F7 number this project has ever
produced rests on a same-session gallery of the *same physical tablets* being matched against
themselves. A central Canadian reference-image gallery would be the poisoned US-image→Canadian-DIN
dependency this project already rejected on other grounds. Muthu, 2026-08-11: *"the moment F7
comes into the picture, the design fails."* It also has an arithmetic hole: a strong relief match
can reach the accept gate without ever confirming an imprint, which is in direct tension with this
project's central safety property (imprint must be *necessary* for verification).

**What would unpark it:** a non-poisoned, formulary-scale Canadian reference-relief gallery. None
is currently sourced or planned.

**Owning doc:** `NB08_Notebook/specs/NB08_DataModel_v3.md` §4.3 (disposition table, F7 row).

---

## 3. Pills with no imprint

**Risk:** a meaningful fraction of the Canadian formulary (887 of 7,055 reference rows, 12.6%)
carries no imprint at all — nothing on the pill's surface to read, ever.

**Status:** out of scope by design, not a defect. A research topic in its own right.

**Why parked:** without an imprint there is nothing this identification approach can verify
against — colour + shape + type alone cannot distinguish a Canadian pill (see the formulary twin
study: colour+shape+type collapse the formulary into 276 appearance classes, with a 64% chance of
at least one look-alike collision in an 8-medication profile). The app's own contract routes a
photographed pill with no imprint to a terminal "cannot identify, check with your pharmacist"
message rather than guessing.

**What would unpark it:** this is a different product problem (e.g. packaging-based
identification, pharmacist-assisted enrollment) rather than a fixable gap in the current imaging
approach. Not scoped.

**Owning doc:** `NB08_Notebook/specs/NB08_DataModel_v3.md` §1.8 and §6.

---

## 4. Non-flash capture

**Risk:** the app forces the camera flash on every capture. Whether disabling it (e.g. for
low-light comfort, or to reduce glare/specular reflection on glossy pills) would help or hurt
identification accuracy is unknown.

**Status:** unanswered, not answered — this is the important distinction. Every identification
number this project has ever quoted was already a 100%-flash number (all 236 scored records
across five evidential sets), so there is no hidden regime mismatch in anything published so far.
But that also means non-flash performance sits at **n = 0**: genuinely untested, not shown safe.

**Why parked:** nobody has proposed shipping a non-flash capture mode, so the question has not
needed answering. It was first mis-recorded as "closed — not a live threat," which invited reading
it as "flash shown harmless" — that reading was wrong and was corrected in the register.

**What would unpark it (or rather: re-open it):** the moment anyone proposes a non-flash capture
regime, this becomes live again and needs a dedicated evidential shoot before shipping. It is not
something that resolves itself over time.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.11.2; `NB08_DataModel_v3.md` §4.3
(disposition table, T4.4 row).

---

## 5. Dual capture (a second, no-flash frame alongside the flash frame)

**Risk:** capturing two frames per pill (flash + no-flash) instead of one, to get a cleaner imprint
read from the no-flash frame while keeping flash for colour.

**Status:** survives only as **strictly additive** work — never a substitute for the current
single-flash-frame pipeline, and not currently scheduled.

**Why parked:** colour scoring depends on flash (the illuminant-estimation code needs a bright,
known-ish light source; removing flash makes the illuminant unknown and variable, and averaging a
flash+no-flash pair produces an ill-posed blend that is *worse* than either frame alone). So any
dual-capture design must route colour from the flash frame regardless of what the second frame is
used for — meaning a second frame can only ever add a (small, ~0.06 correct/crop) imprint-reading
benefit on top of the existing flash-frame pipeline, never replace it. That marginal benefit does
not currently justify the capture-contract change (roughly doubling the capture count) it would
require.

**What would unpark it:** a product decision that the marginal imprint-recovery gain from a second
frame is worth the added capture-contract and app-flow cost. Also blocked on resolving the
confound between the no-flash frame's apparent benefit and the phone's own auto-HDR processing,
which has never been isolated.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.15.12d–§3.15.12e.

---

## 6. `Sample14`'s fate and `Sample13` phone-transfer

**Risk:** two planned evidence shoots — a large-scale (186-frame, 15-DIN) out-of-session gallery
test (`Sample14`) and a different-phone hardware-transfer check (`Sample13`, ~30–50 frames) — are
both still undecided, not cancelled and not scheduled.

**Status:** both deferred, unresolved.

**Why parked:** `Sample14` was sized against a 600+ photo deliverable already committed in an
interim paper, so it cannot simply be dropped, but naming a newer set (`Sample17`) as the
evidential set for a different, more recent experiment did not retire `Sample14`'s original
purpose — whether it still runs, and against what, has been left open on purpose rather than
silently resolved. `Sample13` is the only planned evidence about whether results transfer to a
different phone's camera hardware; it is deferred to after any `Sample14` run, not evaluated on
its own priority.

**What would unpark it:** an explicit scoping decision (Muthu's call) on what `Sample14` still
needs to prove given everything measured on `Sample16`/`Sample17` since it was planned, followed by
scheduling the shoot.

**Owning doc:** `NB08_Notebook/specs/NB08_DataModel_v3.md` §3.1 (the "OPEN" note) and §4.3
(disposition table, Sample13 row).

---

## 7. Alt-colour formulary coverage

**Risk:** the reference data's "alternate colour" field (used when a pill's physical colour
genuinely differs from what a monograph implies, e.g. Motrin reading as either brown or dark
orange) is only populated for pills this project has physically held and inspected — it is
essentially empty across the rest of the ~7,055-row Canadian formulary.

**Status:** parked as a stated, un-hidden limitation — not fixed, and not expected to fix itself.

**Why parked:** populating it correctly requires a human to physically hold the pill and compare
it to the monograph; that discipline is deliberate (an alt-colour value is a claim that a human
verified it), but it means any evaluation number that leans on the alt-colour path being available
is **optimistic relative to the real formulary**, where it mostly will not be.

**What would unpark it:** a scaled-up physical verification effort across the formulary, which is
a data-curation cost, not an engineering one.

**Owning doc:** `NB08_Notebook/specs/NB08_DataModel_v3.md` §1.5.

---

## 8. App-photo calibration (the M0 rendering / studio-to-phone geometry gap)

**Risk:** the specific image-processing pipeline this project measured its identification numbers
against (`M0`: a masked percentile-stretch of a tray-well crop, cut using tray geometry — a
homography, a well index, a fixed pixels-per-millimetre scale) is **not the pipeline the deployed
app actually runs**. The app photographs a single pill on a capture card with no tray and no
well index, going through a different code path entirely.

**Status:** open and unmeasured. Explicitly NOT closed by proxy evidence — verified only by
**reproducing** the tray-based numbers on already-landed crop files, which confirms the
*scoring composition* is faithful but does not measure how the *deployed app's own photos* behave
under the equivalent pipeline.

**Why parked:** the deployment-shaped pipeline did not exist to test against when the frozen
detection/reading thresholds were fitted — the numbers this project quotes were fitted on an
instrument the app does not run. This is stated as a known, unmeasured limitation by explicit
decision (Muthu, 2026-08-11) rather than something the reproduction bar was allowed to paper over.

**What would unpark it:** a shoot or dataset of real app-captured single-pill photos (not tray
crops), scored through the actual `analyze_pill()` deployment path, compared against the
tray-based numbers already on record.

**Owning doc:** `NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8, open item 9.

---

## 9. C4's false-accept guarantee is threshold-dependent, and nothing currently guards it

**Risk:** this project's central safety fix (`C4` / `IMPRINT_NECESSARY`, which blocks a pill from
verifying when its own reference carries no usable imprint) was proven safe by a closed-form
arithmetic argument: without an imprint, the best possible score is 0.45, which is below the 0.70
acceptance gate. That proof is **not unconditional** — it holds only as long as the acceptance
gate stays above 0.45. A future retune of that threshold (e.g. chasing a different accuracy target)
could silently drop it to 0.45 or below and reopen the exact false-accept surface C4 was built to
close, with no test currently in place that would notice.

**Status:** found and recorded 2026-08-11/12; not yet guarded in code.

**Why parked:** the fix is a one-line assertion (refuse to let the acceptance threshold drop to or
below 0.45 while the safety flag is on), but it is a change to committed, shipped matcher
semantics, so it is scheduled to land as part of a bundled release ("the 2.6 bundle") alongside
related fixes rather than as an isolated hotfix.

**What would unpark it:** landing that one-line guard assertion wherever the acceptance threshold
is configured, as part of the next matcher-semantics release.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.17.14.7.

---

## 10. OTC-15-only leaves two open mitigation jobs without a tray set that can test them

**Risk:** this project only physically photographs the 15 over-the-counter products it holds (the
"OTC-15"). Two follow-up measurement jobs — confirming that planned recovery fixes (T2.1/T3.1)
actually recover verifications on held-out data, and confirming that a specific short-reference-
imprint false-accept hazard is reachable at tray scale, not just in held-out formulary math — both
need a physical subject the OTC-15 does not contain (specifically, an orange, non-round tablet).

**Status:** newly identified 2026-08-12. Not a temporary sourcing gap — it is now a **permanent**
constraint, because the project's own subject-sourcing rule is OTC-15-only.

**Why parked:** a tray set (`Sample20_T2T3`) was designed to do this job and was retired
2026-08-12 rather than shot, precisely because it could not be re-scoped to work within the
OTC-15-only rule. Both underlying jobs remain real and are filed as open requirements, not
resolved.

**What would unpark it:** either a product decision to revisit the OTC-15-only sourcing rule for a
narrowly-scoped successor shoot, or a redesign of the two mitigation jobs so neither needs a
subject outside the OTC-15's own colour/shape population.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/data/nb08_images/Tray_Images/Sample20_T2T3/PROVENANCE.md`
§9; `NB08_Notebook/specs/NB08_DataModel_v3.md` §4.3 (disposition table, `Sample20_T2T3` row).

⚠️ **EXTENDED 2026-08-12 (roadmap 2.1) — the same gap now also covers the shape-channel fix.** The
disposition for the 766 shape-unknown reference rows (a same-precedent fix to `score_shape`'s
neutral, see the "Active roadmap" section below) was found structurally unreachable in the current
LOPO-520 population for the same underlying reason as this entry: none of the 15 OTC DINs carry a
blank reference shape. Its confirming population is owed and unsourceable under the same OTC-15-only
rule, not a new constraint.

---

## 11. `dulcolax`'s cost-trap existence proof was never re-scored through the real heads

**What was hit:** roadmap 1.4's measurement found an existence proof that the corroboration cap
could bite a *supported* pill — `dulcolax`'s own true imprinted face exact-matches its own
one-character reference at the deployed rendering (Sample17 TEST, set S14 well 2). But whether the
cap actually **fires** on that record was **not** re-scored, because no real colour/shape head
output exists for it. The closed-form bound makes it plausible; it is **not measured**.

**What it blocks:** the honest answer to *"does the safety fix break M1's own happy-path bar?"*
`dulcolax` is already the only supported pill that never read on Sample17 (0/7 at both deployed
renderings) and its reference imprint is a single character — the weakest happy path and the
sharpest hazard in the supported set, in the same row.

🔴 **THE ASK (Muthu's call, not the SA's):** if re-scoring later shows the cap does fire and
`dulcolax` cannot verify on the happy path, **remove `dulcolax` from
`IMB1_Prototype/NB08_Notebook/data/allowlist/supported_dins.csv`** — a membership decision, made by
Muthu, with this evidence attached. The SA must not edit the allowlist to make a bar pass. The same
question applies to the other two short-imprint supported DINs, `senekot.s` and `asa.81`.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.17.13.8.

---

## 12. ~~A 22-row disagreement between two views of the same formulary count~~ — ✅ **RESOLVED 2026-08-12, same day. Kept as a worked example, not as a live risk.**

**What was hit:** roadmap 1.4's harness measured **5,652** scoreable reference rows where the
previously-published per-length breakdown implies **5,630** (1,206 + 1,429 + 1,609 + 1,386). The
build agent logged the gap and did not chase it.

✅ **RESOLVED by the adversarial pass, and NEITHER SIDE WAS WRONG.** Exactly **22** of the 5,652 rows
carry an imprint with **no alphanumeric characters at all** — punctuation-only entries. 5,652 − 22 =
5,630, matching the published buckets exactly. The harness's own D8 bar already excluded them
correctly; only the *prose* reconciliation was missing.

**Why it is kept here rather than deleted:** these punctuation-only rows are the same artefact class
that, caught earlier in this area, had inflated a different count by ~38% **in the direction of
alarm**. The class recurs. The lesson is the durable part: **partial agreement between two views is
the most misleading signal available** — it manufactures confidence in the matching half and
suspicion of the other. This one resolved benignly; the next may not.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.17.13.5 and §3.17.13.8.

---

## 13. The colour channel's confidence gate costs one verification, and moving it is a configuration call

**What was hit:** the colour fix designed on 2026-08-12 asks the colour classifier to *decide* a
class before that class counts, and it only decides when the class holds a majority of the
posterior — the same 0.5 the matcher already commits for the shape and type channels. On one
photograph of `benadryl`, the classifier reads the **correct** colour but at **0.3874** — right
answer, under-confident — so the design scores it as "no colour evidence" and that photograph stops
verifying. It is the only such loss found, and it appears only when the colour fix runs alongside
the shape fix (T2.1); the colour fix alone still nets **+1** verification with **zero** wrong ones.
Lowering the gate to 0.40 does **not** recover it, so this is a property of having a gate at all,
not of the particular value.

**What it blocks:** nothing outright — the design ships as measured. It is a known, priced cost on
the happy path, and the happy path is the acceptance bar.

🔴 **THE ASK (Muthu's call, not the SA's):** decide whether `colour_conf_neutral` should stay pinned
at **0.5** — matching `shape_conf_neutral` and `type_conf_neutral`, which is why it is not a new
constant — or drop below **0.3874** to admit correct-but-under-confident colour reads. **The SA will
not move it**: tuning a threshold until one record on a burned dev set passes is exactly the
practice this project has ruled out, and the evidence for the lower value is a single photograph.
A real answer needs a set that was not used to design the fix.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.17.15 §F.

---

## 14. Two different copies of the reference spreadsheet are in use, and they disagree

**What was hit:** the evaluation harness reads
`IMB1_Prototype/data/reference/ca_appearance_harmonized_v2.xlsx` (**41 columns**), while the matcher
that actually promotes to production reads
`SB2_Prototype/data/ca_appearance_harmonized_v2.xlsx` (**44 columns**). The measuring copy has **no
`colour_alt` column at all**, and it does not carry the `advil` colour correction recorded as done on
2026-08-07. Nothing in the project named this second copy until now — the same shape of finding as
the day it emerged that a *fourth copy of the matcher* was in the evaluation loop, one layer down.

**What it blocks:** any statement about alternate-colour behaviour drawn from the 520-trial
evaluation. That path is **structurally unreachable** in every number that harness has ever
published — which makes it *unavailable*, not *zero*. It does not invalidate the false-accept
results, which never depended on it.

✅ **PART 1 RESOLVED 2026-08-12 (Muthu, DEC-1, binding): the 44-column `SB2_Prototype/data/
ca_appearance_harmonized_v2.xlsx` IS CANONICAL.** Verified by md5: production `SB2/data/`, the
`archive/2026-08-10_production_snapshot/SB2/data/` snapshot, and `PillSafe/data/` all carry the
OTHER, 41-column file (md5 `e9d09906...`); the prototype copy (md5 `6c168453...`) is the 44-column
one. `ca_appearance_harmonized_v3.xlsx` (C5, roadmap 2.2) stays built on the 44-column copy — it did
NOT decide this, Muthu did, and the build's original hedge ("if this entry resolves for the
41-column copy, v3 must be re-derived") is now moot. **Independently corroborated the same session**:
a cell-by-cell adjudication of all 8 cells where the two v2 copies disagree (`NB08_C5_Reference_
Schema_Build.md` §12, U7) found every divergence resolves in the 44-column copy's favour — it is
either more current (received a correction/adjudication pass the 41-column copy never got) or the
41-column copy carries an already-published, more primitive defect (the senekot.s/allergy.remedy
face-merge). **The 3 extra columns (`imprint_repeat`, `imprint_face_note`, `colour_alt`) promote into
production at E3 as part of the schema migration, not before this decision and not as a standalone
file copy.**

🔴 **THE ASK (Muthu's call, not the SA's) — PART 2 remains open, unauthorised, code not data:**
1. ~~Decide which copy of the reference spreadsheet is canonical~~ ✅ DONE above.
2. 🔴 **Authorise the second fix, which is code, not data.** `src/otc_eval.py::reference_row()`
   builds its return dict from a **hardcoded column list that never selects `colour_alt` — and, as of
   the C5 build (roadmap 2.2), never selects any of the 9 new C5 columns either**
   (`colour_norm_2_capsule_cap`, `colour_norm_2_tablet`, `colour_alt_1`, `colour_alt_2_capsule_cap`,
   `colour_alt_2_tablet`, `ink_deboss_indicator`, `imprint_side2_capsule_cap`, `imprint_side2_tablet`,
   `in_scope`) — so even pointed at the 44-column copy, none of these paths are reachable through this
   function. **Still unauthorised; the SA has not made this edit.**

The v3 reference build (a **new** file, with the v2 copies frozen) is where part 1 naturally lands.

⚠️ **Counts corrected 2026-08-12** — first written as 42/45, verified 41/44. The correct pair was
already on file in `NB08_DataModel_v3.md` §5 from 2026-08-08.

✅ **RESOLVED 2026-08-12, same day, by DEC-1 above — the downstream-consumer hedge below is now
historical, kept for the record.** The C5 reference build (roadmap 2.2) shipped
`ca_appearance_harmonized_v3.xlsx` **built from the 44-column `SB2_Prototype` copy**, because it is
the content superset and the brief instructed it; that build did not itself decide the canonicalness
question. Muthu then decided it, the same session, in the 44-column copy's favour — so
`ca_appearance_harmonized_v3.xlsx` does **not** need re-deriving, and the repair pass that closed
roadmap 2.2 (`NB08_C5_Reference_Schema_Build.md` §12) independently corroborated the choice via the
8-cell adjudication cited above.

⚠️ **A related trap found by execution, worth carrying to any future column:** the C5 spec's literal
`"n/a"` value for `ink_deboss_indicator` is a **pandas NA-sentinel string** — write it, read it back,
and it silently returns null, **indistinguishable from a row that was never populated**. It was
stored as `"not_applicable"` instead. **Never use `"n/a"`, `"N/A"`, `"na"` or `"none"` as a literal
cell value in this project's workbooks** — the reader cannot tell them from absence.

**Owning doc:** `NB08_Notebook/specs/NB08_Identification.md` §3.17.15 §H.

---

## 15. B11's rebuilt content-hash check has a bounded residual gap on two oversized BB3 files

**What was hit:** roadmap 2.1's repair pass rebuilt `bind_sb2p.assert_production_untouched()` from a
decorative max-mtime check to a SHA-256 content hash against `archive/2026-08-10_production_snapshot`
(bar B11 could not fail on its own named defect class before this — see `NB08_Identification.md`
§3.17.16 §I/§J). A byte-for-byte hash of every file was measured and found correct, but too slow to
actually run: `BB3/data/embeddings.f32` (5.6 GiB) and `BB3/data/bb3.db` (2.5 GiB) alone made a single
bars pass multi-minute, before an 18-mutation sweep even starts. The shipped fix hashes files ≤2 MiB
in full and uses a `(size, mtime_ns)` fingerprint for anything larger — every `.py`/`.md`/`.xlsx`/
`.csv`/`.json` a development session could plausibly edit gets full content verification; the two
named large files do not.

**What it blocks:** nothing today — an in-place edit to `embeddings.f32` or `bb3.db` that preserves
BOTH size and mtime_ns exactly is an extremely narrow, not-plausibly-accidental scenario, and no
session in this project's history has ever written to either file outside BB3's own build scripts.
It is a genuine, documented residual, not a claim of full coverage.

🔴 **THE ASK (Muthu's call, not the SA's):** none required now. If either file's size ever changes
categorically (e.g. `bb3.db` grows to require chunked I/O in its own right, or a new similarly-sized
frozen artefact is added to a PRODUCTION tree), revisit whether the 2 MiB cap and the fingerprint
fallback are still the right trade-off — a sampled-chunk hash would close the gap at a smaller
runtime cost than full content, if it is ever judged worth it.

**Owning doc:** `NB08_Notebook/harness/NB08_LOPO_F6F7/bind_sb2p.py` (`_tree_hash`'s docstring owns
the exact threshold and rationale) · `NB08_Identification.md` §3.17.16 §J.

---

## 16. Two-key imprint corroboration has a cost we can measure and a benefit no existing data can exhibit

**What was hit:** roadmap A2 settled build-spec open item 14 by measuring, on 1,195 landed A4c picks
across Sample16 and Sample17, whether an independent transcription (A1/PaddleOCR, zero model calls)
supports the constrained reader's pick. Two results: independent agreement is **0.488 on correct
picks and exactly 0.000 on wrong ones** — 🔴 **CORRECTED (adversarial pass, 2026-08-12): this does
NOT mean the two readers demonstrably do not share a failure mode.** The 15-entry ballot has zero
duplicate surfaces, so an exact wrong-pick match is near-impossible by construction alone; and A1's
read is `partial` (near-miss, consistent-but-incomplete) against the wrong pick's own surface 17/396
times, proving the collision mechanism a shared failure mode would need is not foreclosed. Separation
is real (A1 contradicts the wrong pick 315/396 and names the true pill only 23/396) but partly
structural — full derivation `NB08_Identification.md` §6.8.4. But requiring corroboration before
paying the imprint term would **lose 233/578 (40.3 %) of the correct
reads that succeed today** — while the *benefit* leg, `P(support | gate passed, WRONG)`, has
**denominator 0**, because no wrong pick has ever cleared the frozen margin gate on either burned
set. The benefit is **UNAVAILABLE, not zero** — the same shape as open item 5's `0/0` size-1 safety
leg. 🔴 **NEW (adversarial pass, 2026-08-12): the excluded population is not exchangeable, and it
skews toward MORE wrong picks, not fewer** — 98.4 % of excluded rows are `Pair2` crops, join rate
within `Pair2` is arm-dependent (M0/M0raw 87.5 % vs M1–M5 40.9 %), and excluded picks are 26.6 %
wrong vs 33.1 % wrong for the measured population — the headline is not inflated by the exclusion.
0/102 excluded wrong picks cleared the gate, reinforcing the gate finding outside the measured 76 %.
Design settled on option (a)+(d) instead: SB2 consumes the pick as a typed decision and its
independent contribution is **refusal**, not confirmation.

**What it blocks:** nothing today — step 7 proceeds under (a)+(d) with hardenings H1/H2/H3. What is
blocked is any claim that two-key corroboration (or its cheaper veto-only variant, which costs 29 %
of gate-passing correct reads for the same unmeasurable benefit) is or is not worth its price. That
question cannot be reopened on burned data by construction.

🔴 **THE ASK (Muthu's call, not the SA's):** when the confirmatory shoot of roadmap 0.3 / build-spec
step 10 is authorised, **deliberately include stray and off-ballot pills in enough numbers that some
wrong pick can clear the margin gate.** Without that population the corroboration question stays
permanently unanswerable, and the current ruling stands by default rather than by evidence. A second,
much cheaper ask, independent of any new shoot: **authorise a PaddleOCR-only re-run over the already
landed `Pair2` crops** (no VLM, no new photographs, no new labelling) — A1 was never run on them, so
**383 of 1,578 landed picks (24.3 %) sit outside the measured join** (428 rows are unjoined; 383 of
those are picks, 45 are abstentions — 🔴 CORRECTED, adversarial pass 2026-08-12: the prior "428
picks (26 %)" conflated rows with picks) and the coverage limit is avoidable.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8 open item **14-R**
(the design and the ruling) → `NB08_Identification.md` **§6.8** (every number, denominator and
threat).

---

## 17. A4c stays the identifier; a second, independently-gated identifier is not ready — two candidates evaluated this session, neither built

**What was hit:** Muthu's instruction was to keep A4c as the identifier and record here that a
*second* identifier is needed. This session evaluated why the two obvious candidates are not ready
today, rather than building either.

🔴 **A3 cannot carry it as things stand.** A3 runs on **Ollama**, Ollama exposes **no logprobs**, and
A4c's **PMI margin *is* the safety mechanism** (`NB08_C6_Contract_Build.md:61`) — there is no way to
compute a margin for a model whose runtime will not surface token probabilities. Promoting A3's
glyphs to an identity channel without that margin creates an **ungated identifier**, and §3.15.11
measured ungated readers as the most dangerous configuration this project has tested (ungated A4c:
178 correct but **40 fabrications** on 301 crops, vs 3 for A3 read free-form; gated A4c: 132 correct,
**0** fabrications). 🔴 **A3's sentinel abstention protects against reading *nothing*; it does not
protect against reading *wrong*.** Confirmed on a landed crop: A3 asserted `TEXT` reading **"SAXVOL"**
on well S02_w3, pill `gravol` (a GRAVOL tablet) — a confident, plausible-looking, wrong glyph read,
not a refusal (`results/nb08_c7_repro/stage1_a3_responses.jsonl`, `results/nb08_sample17/reads_A3_test.csv`).

A3's own blank-face record does not rescue it either: on the Sample17 TEST truth-free tables
(§3.16.3a), A3 fabricates `TEXT` on **0/13** blank crops under `M0` and **1/13** under `M0raw`. 🔴
**n=13 is in the same small-sample range this project has already learned not to trust for a
zero-fabrication claim** — §3.14.4 withdrew *"both VLM readers fabricate ZERO"* once a 10-crop
control widened to 70 and found the floor, and §3.15.11 is where the harder count actually surfaced
(ungated A4c 40 fabrications against A3's 3, on 301 crops). A near-clean count at n=13 is not a
safety property.

🔴 **H3 validated A3 as a PRESENCE DETECTOR, not as a reader.** §3.16 frames H3's own question as
*"does this crop carry an imprint"* — a three-way `TEXT`/`UNREADABLE`/`NONE` verdict — and never
scores glyph accuracy. Reading H3's pass as evidence A3 is ready to identify is exactly the
misreading that made A3 look ready when what was actually validated is narrower.

**Surviving candidates, neither built:**
1. **A3 under `transformers` instead of Ollama**, so it can carry its own PMI margin the way A4c
   does. No reshoot needed (same landed crops). Estimated **~6 GB against the measured 8.00 GiB card**
   (`NB08_C6_Contract_Build.md:413` — LEAD, not measured for A3 specifically, scaled from A4c's
   4.44B/8.88 GB bf16 footprint) — the **one-resident-at-a-time arbiter** (`src/nb08_arbiter.py`,
   `NB08_C6_Contract_Build.md` §5) already handles single-model VRAM residency, so this is a
   configuration change, not a new architecture.
2. **A1/PaddleOCR as a gated corroborator.** Architecturally independent of A3/A4c (different
   engine family, no VLM). Already has a fitted recogniser-confidence gate from the §3.17.11
   baseline run. But it is a **weak reader** — **0.401** exact-vs-truth pooled (413/1,029,
   re-derived this session) — and its independence evidence now carries **Repair 3's discount**
   (`NB08_Identification.md` §6.8.4): separation from A4c is real but partly structural, not
   demonstrated failure-independence.

**What it blocks:** any claim that PillSafe has a second, independently-gated identification
channel. A4c remains the sole identifier; SB2 independently refuses (per open item 14-R's ruling)
but does not independently identify.

🔴 **THE ASK (Muthu's call, not the SA's):** decide whether to schedule candidate (i) — A3 under
`transformers` with its own margin — or candidate (ii) — A1 as a gated corroborator — or leave the
need parked here. Neither is scheduled by this entry.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8 open item **14-R**
(A4c's margin mechanism, line 61) · `specs/NB08_Identification.md` §3.14.4, §3.15.11, §3.16 (H3),
§3.16.3a (A3 blank-face fabrication table), §3.17.11 (A1's fitted gate), §6.8.4 (Repair 3's
independence discount).

---

## 18. `ink_deboss_indicator` shipped on 15 gold DINs, not the ~5,049 rows its own spec planned

**What was hit:** `NB08_C5_Reference_Schema_Build.md` §10 step 3 (the build plan, written 2026-08-10)
called for populating `ink_deboss_indicator` from `source_text` cues across **~5,049 of 5,901
`imprint_status='present'` rows (85.6%)**, "with no BB3 call" — a purely mechanical, formulary-wide
extraction, per §3's own coverage table. The roadmap 2.2 C5 build (2026-08-12) shipped it on the
**15 gold OTC DINs only**, under a later, narrower scope instruction (real extracted values for the
11 supported + 4 excluded OTC DINs; the remaining ~7,040 rows migrate structurally, present and
empty). Both are legitimate, documented instructions from different points in the same project — but
they disagree on this one column's reach, and that disagreement was disclosed by the build
(`NB08_C5_Reference_Schema_Build.md` §12, `HANDOFF_2026-08-12.md` §7) rather than resolved. Unlike
the shape backfill (roadmap 2.1, formulary-wide, explicitly re-authorised as a mechanical exception)
and the DEC-2 colour/imprint-side2 split (also formulary-wide, mechanical, explicitly re-authorised
this session), `ink_deboss_indicator`'s wider reach was never re-confirmed after the narrower SCOPE
instruction landed — it is unclear whether the ~5,049-row plan is still wanted, was superseded on
purpose, or was simply not re-raised.

**What it blocks:** any claim that `ink_deboss_indicator` is populated beyond the 15 gold DINs, and
any downstream feature (e.g. an imprint-modality-aware UI hint, or a future comparator term) that
would want it formulary-wide. Does not block anything shipped today — the column is not read by any
scorer (v3 is not wired in), and the 15-gold-only population is honest (no leakage, verified by B7).

🔴 **THE ASK (Muthu's call, not the SA's):** decide whether the ~5,049-row `source_text`-cue
extraction (spec §3's coverage table: present 4,088 deboss-cue + 961 ink-cue rows, none 231+150,
unknown 0) should still run as a mechanical, formulary-wide pass like the shape backfill and DEC-2's
split did, or whether the 15-gold-only scope is now the permanent answer for this column and the
spec's §10 step 3 plan should be marked superseded. Either answer is a scope decision, not an
engineering one — the mechanism (`source_text` cue matching) is already designed and measured in
§3, just not re-authorised for the wider population.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_C5_Reference_Schema_Build.md` §3 (the
~5,049-row coverage measurement) and §10 step 3 (the original plan) · §12 (the repair pass that
disclosed the gap rather than resolving it).

---

## 19. Two real formulary rows carry a blank assessed face (`imprint_side1`) with a present flip
pointer (`imprint_side2`) — possibly a C5 reference defect, not merely a null-handling gap

**What was hit:** an Opus refuter reviewing roadmap 2.3 (C1/C2/C3) found that two real v3 rows
(a third similarly-shaped row is a capsule, already correctly handled by the pre-existing capsule
suppressor — not part of this ask) carry `imprint_side1` blank while `imprint_side2` is present and
`imprint_status='present'`. The CODE-level consequence was fixed the same session (`flip_suppressed`
gained a third rule so a blank assessed face never triggers `ask_to_flip`). But v3 §1.3 states
`imprint_side1` should be the face that narrows the formulary MOST — under that rule, a row with NO
recorded side1 text at all looks like the reference itself may have the two sides reversed, or side1
was simply never captured, rather than a case where "there is genuinely nothing on that face."

**What it blocks:** nothing shipped today (the code-level fix is live and bar-tested, `flip_suppressed`
suppresses correctly regardless of which explanation is true). Blocks a confident answer to "is the
v3 §1.3 side-ordering invariant actually upheld everywhere the schema claims it is," and blocks
deciding whether these two rows should be corrected (side1/side2 swapped, or side1 back-filled) as
part of a future C5 pass.

🔴 **THE ASK (Muthu's call — C5 scope is his, not the SA's):** decide whether these two rows'
blank `imprint_side1` is (a) a genuine "no assessed-face text was ever captured for this product"
state that the schema should represent as-is (current behaviour, and the code-level fix already
handles it safely), or (b) a data entry gap/side-ordering error that should be corrected in a future
C5 pass (e.g. by re-deriving which face actually narrows the formulary most for these two products,
or by checking the source monograph for a missed side1 reading). No formulary-wide sweep is implied
by two rows — this is a targeted, small-N question.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_Identification.md` §3.18's "2026-08-12
REPAIR" subsection (S4) owns the measurement and the code-level fix; `NB08_DataModel_v3.md` §1.3
owns the side-ordering invariant this ask is about.

---

## 20. ~~`DIN13803` (gravol)'s `imprint_repeat` flag is `2.0` in v2 but blank in v3~~ — ✅ **RESOLVED
2026-08-12, same day this entry was found. Kept as a worked example, not as a live risk.**

**RESOLUTION:** the blank in v3 IS the deliberate C5 correction, not a backfill-scan gap. Verified
directly against BOTH workbooks (content, not the register, not an mtime check): `ca_appearance_
harmonized_v2.xlsx` gives `DIN13803` `imprint_repeat=2.0`; `ca_appearance_harmonized_v3.xlsx` gives
the SAME row `imprint_repeat=NaN` (blank), `imprint_side1='GRAVOL'` unchanged in both. This matches
`NB08_DataModel_v3.md` §1.3.1's own table exactly: *"gravol — `GRAVOL`, one straight line —
cross-score, no text — 🔴 `imprint_repeat=2` is FALSE"* — and that same section's reference-corrections
list states the correction is **independently confirmed by `RedTeam_OTC_RefAudit`**, a SEPARATE audit
that found the same false-doubling remediation from the other direction. Two independent sources agree
the `2.0` was wrong; v3's blank is the fix landing, not a bug. Closed as **RESOLVED-BY-DESIGN**, not
carried forward as unknown — the workbook did not contradict this, so no further ask is owed to Muthu.

**Original entry, kept below for the record:**

`DIN13803` (gravol)'s `imprint_repeat` flag is `2.0` in v2 but blank in v3 — found while
building the B1 oracle's v3 leg, not investigated further

**What was hit:** the B1/M7 oracle repair (`oracle_snapshot_diff.py`) added a genuine v3 reference
leg (the sheet the pre-repair harness silently never ran against — a different, code-level defect,
now fixed). Checking where v2 and v3 disagree on the 10 columns the matcher actually reads found
only 3 of 7,055 rows differ on IMPRINT-relevant fields (the other 219 of 222 total differences are
`shape_norm`/`colour_norm`/`colour_alt` — common-mode terms that provably cancel in a proto-vs-
snapshot comparison, so they don't move any number this repair published). Two of the three are
known, deliberate C5 corrections already on record (`DIN2017849`/benadryl's `imprint_side2`
backfilled; `DIN2375990`/allergy.remedy's `imprint_side1`/`imprint_side2` un-inverted — Futureworks
entry 14 and the C5 build history). The third, `DIN13803` (gravol), has `imprint_repeat=2.0` in v2
and blank in v3 — the SAME DIN `matcher.py`'s own F6 docstring names as the motivating case for
repeat-tolerance ("GRAVOL arced twice ... three of five Sample11b items affected"). Whether v3's
backfill scan deliberately withdrew this value or dropped it unintentionally was NOT established —
outside the scope of an oracle repair, which reads both workbooks but must never edit either.

**What it blocks:** nothing shipped today — no live harness currently forces a v3-fed, repeat-
tolerance-dependent decision on this DIN. It is a latent risk for any future v3-only evaluation that
assumes `imprint_repeat` values carried over from v2 unchanged.

🔴 **THE ASK (Muthu's call, not the SA's):** confirm whether `ca_appearance_harmonized_v3.xlsx`'s
blank `imprint_repeat` for `DIN13803` is an intentional C5 correction or a backfill-scan gap: if the
latter, authorise a fix in a future v3 build pass (not something an oracle-repair session should do
— v3 is a workbook this session was told never to modify).

**Owning doc:** `IMB1_Prototype/NB08_Notebook/harness/NB08_C6/oracle_snapshot_diff.py`'s v2/v3 leg
(BAR M7); `NB08_Identification.md` §3.18's "2026-08-12 REPAIR — ROUND 2" subsection.
**Closure:** see the RESOLVED note at the top of this entry — `NB08_DataModel_v3.md` §1.3.1 and
`NB08_Identification.md` §3.19 own the closing evidence.

---

## 21. `sb2.reference`'s deployed default reference workbook stays v2, not v3 — a parked decision, not
## an oversight

**What was hit:** step 7's repair pass (2026-08-12, `c6_adapter.py`) fixed `sb2.reference._load`'s
sheet-name resolution so `get_candidates(..., xlsx_path=<v3 workbook>)` no longer raises (it hardcoded
`sheet_name="harmonized"`, absent from v3's single `Sheet1` — the same defect
`oracle_snapshot_diff.py`'s own BAR M7 already fixed for its own loader). The repair deliberately did
**NOT** change `sb2.reference._DEFAULT_XLSX`, which still points at
`ca_appearance_harmonized_v2.xlsx` — the file every deployed call to `sb2.match_pill`/
`c6_adapter.match_c6` actually reads.

**What it blocks:** repointing the default is coupled to the C4/comparator promotion (the D4 bundle,
roadmap 2.6) — v3 carries C5's ordered-sides columns and other corrections that the D4 bundle's own
K1 re-run (roadmap 2.4) needs to isolate cleanly. Changing the default here, inside an adapter-only
repair pass, would silently fold that comparator change into a step scoped to NOT touch it.

⚠️ **Measured harm today: VACUOUS, and this is now bar-enforced, not merely observed.** A new bar
(`GROUP REF`, `harness/NB08_C6/test_c6_adapter.py`) compares v2 and v3 on every field `c6_adapter.py`
actually reads (`colour_norm_1/2`, `colour_alt`, `shape_norm`, `type_norm` — never `imprint_side1/2`,
which this adapter's scoring never touches) across the real 11-DIN OTC-15 supported profile: **0 of 55
cells differ.** A second bar (`REF-EQUIV`) runs the full adapter decision twice, once sourced from each
workbook, under the actual deployed configuration (no `label_to_din` supplied — see entry-in-progress
on the tenth vacuity mechanism, `HANDOFF_2026-08-12.md` §3.6) and requires byte-identical output;
VACUOUS today, but this is the tripwire that would go red the moment either reference's adapter-read
columns diverge in a way that reaches scoring.

🔴 **THE ASK (Muthu's call, not the SA's):** authorise repointing `sb2.reference._DEFAULT_XLSX` to v3
when the D4 bundle (roadmap 2.6) is ready to promote — not before, and not as a side effect of any
future adapter-only step. Until then this entry stays open as a reminder that the sheet-loading FIX
and the DEFAULT-repoint DECISION are two different things, deliberately not bundled together.

**Owning doc:** `SB2_Prototype/sb2/reference.py` (`_load`, `_DEFAULT_XLSX`); `NB08_Identification.md`
§3.19 "2026-08-12 REPAIR" subsection (owns the 0/55 measurement and the `REF-EQUIV` tripwire);
`harness/NB08_C6/test_c6_adapter.py` GROUP REF.

---

## 22. `match_c6`'s candidates-vs-profile guard has no redundancy in the DEPLOYED (null-map) call
## shape — a single point of protection, not a bug

**What was hit:** the STEP 7b BUILD refuter (2026-08-13, finding 7, "THE SAFETY ITEM"). Under the
call shape production actually uses today (`label_to_din=None` — confirmed, the sidecar,
`PillSafe/dev/brains/app.py:377`, still calls `sb2.match_pill(record, dins)` with no map),
`sb2.c6_adapter._assert_map_within_profile` is a documented no-op (`if not label_to_din: return`,
by design — "no map" must stay reachable, GROUP REF's `REF-EQUIV` bar depends on it). So
`_assert_candidates_within_profile` (the F2 two-list guard) is the SOLE protection against a caller
passing candidates that do not match the record's declared profile, in this configuration. MEASURED
by execution, both legs, `harness/NB08_C6/test_label_map.py` bar `PROV-7`: (1) baseline, correct
code, null map, out-of-profile candidates — STILL raises (the candidates guard alone handles it
fine today); (2) with the candidates guard monkey-patched out (`mutate_c6_adapter.py`'s own `D14`
mutation shape) AND null map — NOTHING raises; `match_c6` silently returns a `reject` decision
instead of refusing. `mutate_c6_adapter.py`'s existing `D14` mutation is caught by
`test_c6_adapter.py`'s own fixture ONLY because that fixture happens to also violate the NEW map
guard (a real map, `CLUSTER_LABEL_TO_DIN`) — an unrelated coincidence, not evidence the null-map
shape is independently guarded. Re-measured directly against the null-map configuration: D14 is
13/14, not the 14/14 the existing battery headline reports.

**What it blocks:** nothing shipped today is unsafe — the fixture `test_c6_adapter.py` uses IS a
real map, so the accidental catch is real for THAT fixture, and `_assert_candidates_within_profile`
itself is correct, un-mutated code. What is blocked is a REDUNDANCY guarantee: if
`_assert_candidates_within_profile` were ever regressed (removed, monkey-patched, refactored away)
in the deployed null-map path, nothing else in this module would catch it. This is an architecture
question (add a second, independent check vs. rely on the mutation battery + code review as the
safety net), not a defect in STEP 7b's own work — DEC-6's "structural, not merely tested" standard
does not currently extend to this specific guard's redundancy.

🔴 **THE ASK (Muthu's call, not the SA's):** authorise (a) adding a second, INDEPENDENT
candidates-vs-declared-profile check inside `match_c6` that does not share `_assert_candidates_
within_profile`'s function object (so a single-point mutation/regression there cannot silently
disable both), accepting the added code-duplication risk that creates; OR (b) explicitly accept
that `_assert_candidates_within_profile` is the sole, single-point guard for the null-map call
shape, protected only by the mutation battery (`mutate_c6_adapter.py`'s `D14`) and code review, not
by runtime redundancy — and record that acceptance here as the closing decision. Either answer
closes this entry; no answer is unsafe today, both are legitimate engineering postures.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/harness/NB08_C6/test_label_map.py` bar `PROV-7`
(measures both legs, added 2026-08-13) · `SB2_Prototype/sb2/c6_adapter.py`
(`_assert_candidates_within_profile`, `_assert_map_within_profile`, `match_c6`) ·
`NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8 "STEP 7b" (design) ·
`NB08_Notebook/specs/NB08_Identification.md` §3.19 (BUILD REFUTED → REPAIRED subsection owns the
measurement).

---

## 23. 🔴 HIGH PRIORITY / MVP-CRITICAL — "PATH A": multi-pill capture is built for the research
## card but not carried through the app contract; Muthu names this the most critical MVP gap

**Status correction, 2026-08-14 (Muthu, overriding the SA's initial framing below the line):** the
SA's first pass at this entry treated the missing capability as a low-priority, maybe-never "M2 or
later" question, on the grounds that no real patient owns a calibrated 6-well ArUco card. **That
objection is withdrawn — it aimed at the wrong deployment context.** Muthu's ruling, verbatim in
intent: *"PathA to be written into futureworks.md — that is the most critical aspect that an MVP
has to support. This is a college project and does not need patients with pill trays; we only need
to have it in our hands during capstone and competition demos."* For a capstone/competition demo
the card is a PROP Muthu holds himself — there is no patient-distribution problem, so this is a
real, near-term MVP requirement, not a deferred nice-to-have.

**What was hit:** the deployed chain (`IMB1_v0/imb1/__init__.py:45` `analyze_pill()`, the sidecar's
`POST /pill/analyze` at `PillSafe/dev/brains/app.py:324`) is **structurally single-pill** — one
image in, one `{detected, ...}` record out, full stop. Multi-pill capability **already exists and
already works** as a research instrument: `IMB1_Prototype/NB08_Notebook/src/nb08_wells.py`
implements per-well occupancy against a **known 6-well card geometry with ArUco markers** — this is
exactly the card Muthu would hold at a demo. It has simply never been carried through the
IMB1-to-app contract. (Separately, and NOT what this entry is asking for: a GENERAL "find any
number of pills anywhere in an arbitrary photo" picker was measured and killed in this project —
frozen 0/36, geom 7/36, bright 12/36 at IoU>=0.5 against a required bar of >=22/24. Path A does not
need that; it needs the KNOWN-geometry well-occupancy code that already ships.)

**Confirmed by execution** (2026-08-13/14, this session): 8 full Sample17 tray frames (6-well
scenes, the exact card geometry `nb08_wells.py` targets) pushed through `imb1.analyze_pill()`
directly — 8/8 `detected: true`, but because `analyze_pill()` has no well-aware entry point, FastSAM
picked one small, arbitrary region per frame instead of all 6 wells; 2/8 happened to verify a DIN
genuinely in-scene, 0/8 false-accepted a wrong drug. This is exactly the "single-pill code pointed
at a multi-pill scene" failure mode Path A would fix by giving the reader the well geometry instead
of asking FastSAM to guess it. Full measurement: `IMB1_Prototype/NB08_Notebook/archive/demoprep/
02a_tray_probe.md` and `archive/demoprep/02_tray_probe_raw.json`.

**What it blocks:** multi-pill capture as an app entry point — per Muthu, **the most critical thing
an MVP has to support**, for capstone and competition demos (photograph the whole card, get all N
identifications back in one shot, rather than one pill at a time). It does not block the M1
smoke-test bar itself (≥5 single-pill identifications, already achievable per Unit 2's OTC-image
qualification), but it blocks the more impressive demo capability Muthu wants in hand.

🔴 **THE ASK (an action for Muthu):** approve roughly **one week of build-and-test** to carry the
existing 1-pill contract to 1→N end to end:
1. `analyze_tray()` in `IMB1_v0` (new entry point alongside `analyze_pill()`) — wraps
   `nb08_wells.py`'s per-well occupancy + crop, then runs the existing single-pill pipeline per
   occupied well.
2. The IMB1-to-SB2 contract going 1→N: today's record is a single dict; a tray call needs a
   list-of-records, each independently matched against the profile.
3. The sidecar (`PillSafe/dev/brains/app.py`) returning a list from a new `/pill/analyze_tray` (or
   an N-aware `/pill/analyze`), not the current single `{record, match}` shape.
4. The frontend rendering N results in one screen instead of one.
5. **N sequential reader passes under the arbiter's one-model-resident-at-a-time GPU constraint**
   (`src/nb08_arbiter.py`) — N wells means N model loads/swaps in sequence, not parallel; this is a
   real latency cost, not just a wiring change.

🔴 **Honesty check, stated so this entry cannot be over-relied on:** the ~1 week estimate above is
**Muthu's judgment call, not a measured engineering estimate** — no task-level build was scoped or
timed for this entry. The bulk of the real work is items 2-4 (the contract ripple and the bars/
mutations a change of that shape requires under this project's own discipline), not item 1 (the
segmentation itself, which already works today in `nb08_wells.py`).

**Owning doc:** `IMB1_v0/imb1/__init__.py` (`analyze_pill`, where `analyze_tray` would live) ·
`PillSafe/dev/brains/app.py:324` (`/pill/analyze`, the contract that needs to go 1→N) ·
`IMB1_Prototype/NB08_Notebook/src/nb08_wells.py` (the already-working known-geometry well
occupancy this entry proposes to carry through) ·
`IMB1_Prototype/NB08_Notebook/src/nb08_arbiter.py` (the one-model-resident GPU constraint item 5
must respect) · `IMB1_Prototype/NB08_Notebook/archive/demoprep/02a_tray_probe.md` and
`00_DEMO_STORY.md` (this session's measurement and demo framing).

ADDENDUM 2026-08-14 (dated addendum -- augments this entry, does not duplicate it): the single-model
reader (4.4B only, per `DEPLOY_GUIDE_M1_TwoStageReader.md`) removes the model-swap cost that
originally motivated batching reads by pipeline stage rather than by well -- batch-by-stage should be
kept only as a fallback if the 8.8B two-stage path is ever restored (`PILLSAFE_STAGE1=ollama`).
Muthu's binding UX spec for the tray flow, his call: for a pill found in well k, user-facing messages
read "(k+1)th slot" (1-indexed for the user); each slot gets its own alert plus a pharmacist-consult
hedge; and a tray-flow NONE result routes to Flip/Reshoot rather than terminating -- a deliberate
deviation from the single-pill path's terminal-NONE behaviour (ADR 2026-08-14, `.claude/pillsafe-adr.md`).
Measured this session: tray crops pushed through the existing single-pill path scored 0/50 -- the
fail-safe held, no false accepts -- confirming tray frames are native ONLY to the future per-well tray
flow, not to `analyze_pill()` as it exists today. Per-well partial-failure isolation (one well's
failure must not sink the other N-1 results) remains the unnamed hard requirement Path A has to
satisfy, and is not yet named as its own explicit build item in the numbered list above.

---

## 24. No dose-schedule / already-taken enforcement exists anywhere in the pill-scan path

**What was hit:** M1 sprint DEMOPREP (2026-08-13/14), Unit 3. Muthu's own scenario: *"if the
patient has to take two pills in the afternoon per his prescription/profile and he is taking photo
of 3 of the 9 pills, the app should stop the user from taking the 3rd pill."* Read, not assumed:
`app/api/v1/routes/pill.py`'s `POST /analyze/pill/v2` builds `profile_dins` from **every**
`din_confirmed` active prescription (`prescription_service.list_active_for_patient`), with **no
time-of-day, dose-count, or "already scanned today" filter at all** — any confirmed DIN in the
profile verifies at any time, unlimited times. `Prescription.max_daily_dose` and `specific_times`
exist (parsed from the label, stored, and only used to render static instructional text in
`app/api/v1/routes/instructions.py`) — they are display copy, not a gate. No table, column, or
service anywhere in `dev/backend/app` tracks "doses taken today" or counts scans against a
schedule. Grepped for `already_taken`, `dose_limit`, `doses_today`, `taken_today` across
`dev/backend/app` — zero hits outside the display-text usage of `max_daily_dose` already named.

**What it blocks:** the exact demo beat Muthu asked for (scan pill 1 and 2 for the afternoon slot,
then a 3rd scan of a pill NOT due that slot gets refused) cannot be shown as real app behaviour —
today the 3rd scan would simply verify normally, same as the first two, if it's a confirmed profile
DIN. This is correctly **out of M1's bar** (M1 = ≥5 supported pills identified correctly; this is a
new requirement layered on top) and per this session's own brief, is NOT being built here.

🔴 **THE ASK (Muthu, not the SA):** decide whether dose-schedule enforcement becomes a real
requirement (M2 or a later milestone) and, if so, whether it should be: (a) a hard BLOCK (refuse
the scan / mark it non-verifying) when a photographed pill's DIN has no dose due in the current
time window, or (b) a soft WARNING (verify normally, but surface "this isn't scheduled right now,
take it anyway?") — a clinical-safety-vs-usability call that is scope, not evidence, and belongs to
you. Until decided, the DEMO_RUNBOOK narrates the intended moment but marks it explicitly
UNIMPLEMENTED so nobody mistakes a scripted pause for real enforcement.

---

## 25. `IMB1_v0`'s own OCR subprocess crashes on non-ASCII PaddleOCR output — a real, reproducible
## production reliability bug, not a demo-script issue

🟢 **CLOSED 2026-08-13 (FIX-NOW, M1-RCA precondition: systemic/any-pill, not per-pill).** Both legs
fixed in `IMB1_v0/imb1/ocr_sub.py` (child: module-level `sys.stdout`/`sys.stderr`
`.reconfigure(encoding="utf-8", errors="replace")`, point-of-output not call-site) and
`IMB1_v0/imb1/__init__.py::_run_ocr_subprocess` (parent: explicit `encoding="utf-8",
errors="replace"` replacing bare `text=True`, plus a `PYTHONIOENCODING`/`PYTHONUTF8` env override on
the child). All 4 known-crashing images now pass with the non-ASCII glyph reaching `imprint_reads`
intact, not stripped. Mutation-tested: 3/3 distinct reds. Full account, every number, and a
mechanism correction found mid-repair (the parent leg's real failure mode is a silently-swallowed
background-thread decode, not the synchronous exception first assumed): `specs/NB08_Identification.md`
§3.19.1 "FIX-NOW" · `NB08_STATE.md` §5 (2026-08-13 row) · ADR 2026-08-13 (pointer entry).

**What was hit:** M1 sprint DEMOPREP (2026-08-13/14), Unit 2's OTC single-pill qualification probe.
`analyze_pill()` (`IMB1_v0/imb1/__init__.py:37`) spawns the imprint-OCR subprocess with
`subprocess.run([sys.executable, "-m", "imb1.ocr_sub", ...])` and **no environment override at
all** — no `PYTHONIOENCODING`, no `encoding="utf-8"`. `imb1/ocr_sub.py:114` then does
`print(f"[ocr_sub] {args.crop} -> {reads}", flush=True)`, and on this Windows machine (system
default codepage cp1252) that `print()` raises `UnicodeEncodeError: 'charmap' codec can't encode
character ...` whenever PaddleOCR's real-detected `reads` string contains a character outside
cp1252 — measured live, 4 separate times across 52 real single-pill card photos (a bullet `●`
twice on two different DINs, a CJK character `盈` once, and a fourth crash on a 4th image), each
crashing the subprocess (`rc=1`) and making `analyze_pill()` raise, which the sidecar's `/pill/analyze`
(`PillSafe/dev/brains/app.py:358`) turns into an HTTP 422 `PILL_ANALYSIS_FAILED` for the whole scan
— not a low-confidence read, a hard failure. Full evidence: `IMB1_Prototype/NB08_Notebook/archive/
demoprep/02_otc_probe_raw.json` and `02_otc_musclehback_extra_raw.json` (this session's raw probe
output, tracebacks included).

**This is not specific to the DEMOPREP probe script.** The subprocess call and the crashing
`print()` line are both inside the frozen `IMB1_v0` package itself, on the exact code path
`/pill/analyze` uses in production — any real user photo whose imprint OCR happens to emit a
non-cp1252 character (PaddleOCR occasionally emits stray Unicode noise on a low-contrast or
partially-legible imprint, which is common) will crash that scan today, on the actual deployed
sidecar, not just in this session's test harness.

**What it blocks:** reliability of the pill-scan path under the exact conditions (low-contrast,
partially-legible imprints) where a correct "we couldn't read this clearly" abstain is most needed
— instead the scan hard-fails. It also cost this session 4 of 52 candidate qualification attempts
outright (counted as errors, not as abstains, in `02_image_qualification.md`).

✅ **THE ASK — GRANTED AND DONE, 2026-08-13.** Muthu lifted the write-into-`IMB1_v0` rule for this
sprint specifically for this fix. Landed as BOTH options together, not either/or — a build-refuter-
style mutation battery showed a one-leg fix is not enough on this call path (the parent's own
belt-and-suspenders env override made a child-only mutation invisible to testing until the test was
re-targeted at a direct `python -m imb1.ocr_sub` invocation, which has no such override). See the
CLOSED banner at the top of this entry and `specs/NB08_Identification.md` §3.19.1 for the full
account, including a mid-repair correction to the parent leg's assumed failure mechanism.

**Owning doc:** `IMB1_v0/imb1/__init__.py` (`_run_ocr_subprocess`, the spawn site) ·
`IMB1_v0/imb1/ocr_sub.py:114` (the crashing `print`) · `PillSafe/dev/brains/app.py:358`
(`PILL_ANALYSIS_FAILED`, where this surfaces to a user) ·
`IMB1_Prototype/NB08_Notebook/archive/demoprep/02_image_qualification.md` (where the 3 crashes are
counted per-image).

**Owning doc:** `PillSafe/dev/backend/app/api/v1/routes/pill.py` (`analyze_pill_v2`) ·
`PillSafe/dev/backend/app/models/prescription.py` (`max_daily_dose`, `specific_times`) ·
`PillSafe/dev/backend/app/api/v1/routes/instructions.py` (where `max_daily_dose` is actually
consumed today — display text only) · `IMB1_Prototype/NB08_Notebook/archive/demoprep/03_prescriptions.md`
(this session's designed-but-unenforced afternoon-2-meds scenario).

---

## 26. The full 11b/12a/12b burned-set regression (roadmap 2.6, D4) is DEFERRED — a deliberate cut, not a silent gap

🟡 **DEFERRED 2026-08-13, recorded as a cut with its reason (M1 sprint directive 6: "cut short every
test scope as much as possible... never cut a bar that can actually fail").** The original D4 bundle
spec (`HANDOFF_2026-08-12.md` §2, D4 row, as first written) called for re-running every burned-set
regression across the Sample11b/12a/12b family — 236 records × arms, hours of model loads — before the
bundle could be considered assembled.

**What was hit:** the sprint's own leanest-path directive names a detached, hours-long background job
as structurally too big for this sprint ("If a verification leg wants a detached background job, it is
too big — cut it"). The 11b/12a/12b family requires real attribute-head model loads across hundreds of
records and arms, which does not fit that constraint.

**What replaced it, same session (`NB08_Identification.md` §3.20):** two cheaper, execution-based legs
that answer the questions the sprint actually needs answered for M1 — (1) flags-off byte-identity,
proven over two independent passes of 42 real demoprep records plus every per-flag no-op bar already
carried by `test_c1c2c3.py`/`test_c6_adapter.py`/the new `test_t21_t31.py`; (2) the primary measurement
— do the 9 demo DINs still verify with the bundle on — over demoprep's already-captured attribute
reads, zero new model calls, four flag configurations. This is a NARROWER population (45 images, 9
DINs) than the deferred regression (236 records, the full burned-set family) and a DIFFERENT question
(does the bundle preserve/improve the SPECIFIC demo happy path, not does it preserve the FULL burned
corpus's decisions) — reported as such, not presented as a substitute measurement of the same thing.

**What it blocks:** confidence that the bundle (specifically T2.1/T3.1's shape/colour changes and C4's
stricter no-redistribution rule) does not silently regress a decision somewhere in the 236-record
burned family that the 45-image demo population never exercises. The K1 re-run (roadmap 2.4, L1=C3,
`NB08_Identification.md` §3.18 "K1 RE-RUN") already covers `ORDERED_SIDES`/`ASK_TO_FLIP_V2` specifically
against this same 236-record family (0/236 decision moves) — **T2.1/T3.1/C4 have NOT been run against
it.**

**THE ASK (for Muthu):** if the full burned-set regression is wanted before `SB2_Prototype/` →
`SB2/` promotion (L4a), it should run as its own scheduled, non-blocking pass (the sprint's own
"detached job = too big, cut it" rule applies to THIS session, not necessarily to a later one with more
runway) — scope: T2.1 + T3.1 + C4 together, over Sample11b/12a/12b/12b_Set1/15 (the harness-supported
5-set family `eval_e2e.py` already enumerates, per the K1 re-run's own resolution of "6 burned sets").
If skipped, that is also a legitimate M1 call (D-1: leads are enough, provided labelled) — but it should
be a stated decision, not an assumption that the 45-image demo measurement already covered it.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_Identification.md` §3.20 (the D4 bundle
assembly, owns the 45-image measurement this entry contrasts against) · `harness/NB08_FixEval/eval_e2e.py`
(the harness-supported 5-set family, if this regression is run later) · `HANDOFF_2026-08-12.md` §2
(D4 = 2.6 row, records this deferral in place).

---

## 27. Frontend droplet ship completion -- image built, deploy not yet run

**What was hit:** the About-page / C4-diagram change was committed 2026-08-12, but no container image
had been built from it since 2026-07-30 -- the committed source and the running droplet diverged for
two days. As of this session, both frontend and backend images are pushed to GHCR under tag
`20260814-1020`.

**What it blocks:** the live site (`mypillsafe.ca`) still serves the 07-30 image; the About page / C4
diagram change is not visible to any real visitor until the droplet is updated.

THE ASK (Muthu, ~5 min): run the droplet paste block -- bump `IMAGE_TAG` to `20260814-1020`,
`compose pull` + `up` the frontend container ONLY, then restart the gateway nginx (it resolves the
frontend upstream once at container startup, so it 502s after a plain container recreation without an
nginx restart). Verify `https://mypillsafe.ca/architecture-c4-v9b.svg` returns 200 afterward. Rollback
tag if needed: `20260730-1020`.

Before any future FULL `up -d` (out of scope for this frontend-only step, flagged so it is not missed
later): the `20260814-1020` backend image enables admin-gated registration. Set
`REQUIRE_ADMIN_APPROVAL=false` in the droplet `.env` (or configure `ADMIN_EMAILS`/SMTP) first, or new
signups will be silently gated with no admin able to approve them.

**Owning doc:** `documentation/deployment/DEPLOY_GUIDE.md` (`REQUIRE_ADMIN_APPROVAL`, droplet
compose/env section).

---

## 28. Sidecar scheduled task does not auto-start after reboot

**What was hit:** the `MyPillSafe Sidecar` Windows scheduled task is configured for interactive-logon
start only, not boot start. Proven 2026-08-14: after a reboot, `schtasks /query` showed
`Last Result: 1073807364` (0x40010004 -- process terminated by the reboot), and the sidecar only came
back after a manual `schtasks /run /tn "MyPillSafe Sidecar"`.

**What it blocks:** any reboot (planned or a crash) silently takes the sidecar down until someone
notices and runs it by hand -- no automatic recovery.

THE ASK (Muthu): reconfigure the task for boot-time auto-start rather than logon-only, and consider a
tailnet bind-retry in case the network interface isn't up yet when the task fires. Also worth adding:
an automatic warm-up call after start, since the cold first scan measures at 43-81 s.

**Owning doc:** `documentation/deployment/postrestartchecklist.md`.

---

## 29. DIN token normalization at the sidecar API boundary

**What was hit:** `/pill/analyze` silently false-rejects (`faces: []`) when `profile_dins` is not
already in SB2 token form (`DIN` + unpadded integer, e.g. `DIN13803`). The backend's own caller
converts via `dev/backend/app/services/din_utils.py::to_sb2_token` before it ever reaches the sidecar,
but any hand-rolled caller (curl, a harness script, a future integration) that skips that conversion
gets a false `reject` with empty `faces`/`ranked_candidates`, HTTP 200, `detected: true` -- reading as
a clean negative result rather than a format error.

**What it blocks:** nothing in the current production path (the backend already normalizes), but it is
a live footgun for anyone calling the sidecar directly, and it currently fails silently rather than
loudly.

THE ASK (Muthu): decide whether the sidecar should normalize DIN tokens itself at the API boundary
(accept padded/bare/prefixed forms), or should instead fail loudly (a clear 4xx) on an unrecognized
token shape instead of returning an empty-but-200 result.

**Owning doc:** `documentation/deployment/DEPLOY_GUIDE_M1_TwoStageReader.md` triage table (CHECKPOINT 9
callout / DIN token mismatch row, 2026-08-14).

---

## 30. Owed post-demo evidence ledger

Pointer entry, not a copy -- the register lives in
`IMB1_Prototype/NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8, "OWED POST-DEMO" (Addendum 3b,
2026-08-14). It lists mutation runs M2/M3 with captured reds, the w6/w7/w3 re-runs, and the NB08_38
notebook pass 2 / spec result tables -- all code-complete but not re-run before the live demo, under
the sprint's own priority cut. Nothing on that ledger may be quoted as evidence until it actually runs.

THE ASK (Muthu): schedule the owed re-runs when there is runway; until then, treat every item on that
ledger as code-complete-not-verified, not as passing.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8 "OWED POST-DEMO".

---

## 31. Qual formal report

**What was hit:** the round-2 qualification results
(`results/nb08_demo_qual/qual_results_round2_clean.csv`) landed and the runbook was stamped, but no
formal report section was ever written summarizing what that qualification round found. Separately,
the first round-2 run was condemned (contaminated instrument) and produced `qual_results_round2.csv`
(not `_clean`) -- that condemned run should be referenced from the register as a caution, not silently
left alongside the clean one with nothing distinguishing them.

**What it blocks:** anyone reading the qual results cold has to reconstruct the story from the raw
CSVs and runbook stamps rather than a written summary; the condemned first attempt is not currently
flagged anywhere a future reader would see it before reusing the wrong file.

THE ASK (Muthu): schedule a short formal report section (what was tested, what passed, what the
round-1-contaminated / round-2-clean distinction means) and add a one-line caution pointing at the
condemned run from the register.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/results/nb08_demo_qual/`
(`qual_results_round2_clean.csv`, `qual_results_round2.csv`, `QUAL_PLAN.md`).

---

## 32. UI minors from E2E (2026-08-14)

**What was hit:** two small UI defects found during end-to-end testing on 2026-08-14: (a) the "Needs
your review" badge never flips after an Approve action -- the backend state is correct, but the UI
does not reflect it without a manual refresh/re-navigation; (b) a stale JWT renders a blank dashboard
instead of redirecting the user to `/login`.

**What it blocks:** neither breaks a demo happy path outright, but both are visible rough edges a real
user (or a judge) could hit.

THE ASK (Muthu): schedule both as small frontend fixes -- (a) re-fetch or optimistically update review
status after Approve; (b) detect an expired/invalid JWT on dashboard load and redirect to `/login`
instead of rendering an empty state.

**Owning doc:** `documentation/deployment/E2ETestingFindings.md` if it already tracks this session's
run, else this entry is the record.

---

## 33. Numeric-drift version-attribution study

**What was hit:** 4.4B model reads drift across different `transformers` / `torch` / `bitsandbytes`
version triples. Outcome-level bars (pass/fail on the acceptance decision) passed across the triples
tested, but byte-level reproduction of the exact scores failed, and every verdict flip observed was
conservative (toward rejecting, not toward a false accept).

**What it blocks:** nothing production-blocking today -- this is a paper-relevant robustness question
(how sensitive are the published numbers to the exact dependency pin), not a safety gap in the shipped
bar.

THE ASK (Muthu): schedule a one-variable-at-a-time attribution study (hold two of the three versions
fixed, vary the third) to identify which dependency actually drives the drift, when there is runway for
a paper-facing robustness section.

**Owning doc:** `IMB1_Prototype/NB08_Notebook/specs/NB08_C6_Contract_Build.md` §8, open item
(numeric-drift / version-attribution).

---

## 34. `/pillsafe` activation blurb is stale

**What was hit:** the `/pillsafe` persona's activation text still lists OB5 DIN-linking, CB4, and BB3
guards as live, in-progress fronts. All three have since closed (2026-07-22 / 2026-08). Anyone
activating the persona cold reads a status that is several weeks out of date.

**What it blocks:** nothing functional -- this is a persona-activation-text accuracy issue, not a code
or data risk. But a stale activation blurb misdirects the very first thing a new session reads.

THE ASK (Muthu): next session, update the activation text in `C:\Users\muthu\.claude\commands\pillsafe.md`
to reflect current front status instead of the OB5/CB4/BB3-in-progress framing.

**Owning doc:** `C:\Users\muthu\.claude\commands\pillsafe.md`.

---

## 35. NF4 loader crash -- memory/commit pressure alone reproduces the failure signature on the main thread (addendum to the scorer warm-on-signin entry below)

**What was hit:** T09 evidence, 2026-08-15 -- a dedicated reproduction run isolated memory/commit
pressure as a variable independent of thread context, and it alone reproduces a same-signature
failure on the MAIN thread: an `OSError` (WinError 1455, "the paging file is too small") raised
inside `safe_open`, captured at ~1.7 GB free RAM with 36 of 43 GB total commit already in use.
Windows Error Reporting shows both of today's production crashes faulting inside `torch_cpu.dll` at
the identical offset `0x8e4a279`. `pip freeze` from the crashing environment is byte-identical to
the 2026-08-14 qualified snapshot, ruling out a dependency-drift explanation. Net effect: **the
worker-thread mechanism named in the scorer warm-on-signin entry below is unproven-innocent, not
exonerated** -- memory pressure alone is sufficient to reproduce the crash signature even off the
worker thread, so the original diagnosis (lazy load on a uvicorn worker thread) is not the only path
to this failure.

**What it blocks:** confident selection of a single-cause fix. Five candidate repairs were ranked,
not chosen: (1) warm-at-boot eager load -- **recommended**; (2) a pre-load headroom guard (refuse to
load below a free-RAM floor); (3) event-loop-thread pinning -- **would NOT have prevented today's
crashes**, since the reproduction ran main-thread; (4) pagefile/ops-level sizing; (5) a
`torch`/library upgrade -- **no evidence** it addresses this offset.

🔴 **THE ASK (Muthu's call, not the SA's):** owner deferred the re-arm decision entirely on
2026-08-15 -- no repair is authorized yet. When runway exists, pick from the five ranked repairs
above (warm-at-boot is the SA's recommendation) and authorize it explicitly; this entry and the
scorer warm-on-signin entry (Active roadmap, below) should close together.

**Owning doc:** the "Scorer warm-on-signin" entry under **Active roadmap** below (same underlying
defect, filed 2026-08-15, MPR1 session) · `NB08_Notebook/results/nb08_tray_route/run3/` (original
evidence) · T09 reproduction run, 2026-08-15 (this addendum's evidence).

---

## 36. Dormant Stage-1 fallback booby trap -- `qwen3-vl:latest` removed from Ollama, `PILLSAFE_STAGE1=ollama` still names it

**What was hit:** `qwen3-vl:latest` (8.8B) was removed from the local Ollama model store on
2026-08-15, freeing +5.71 GB. `production_wiring.py`'s `build_reader()` still has a
`PILLSAFE_STAGE1=ollama` branch that names that exact tag as its Stage-1 model.

**What it blocks:** nothing today -- the branch is not the active configuration (the single-model
4.4B reader is production, per `DEPLOY_GUIDE_M1_TwoStageReader.md`). But the branch is now a
**dormant booby trap**: if anyone ever flips `PILLSAFE_STAGE1=ollama` back on (e.g. chasing the
two-stage reader's earlier accuracy profile, or during an incident-response rollback) without first
re-pulling the tag or patching the code, `build_reader()` will 404 against Ollama at first call, not
at config load -- a runtime failure discovered mid-incident rather than at flip time.

🔴 **THE ASK (Muthu's call, not the SA's):** decide whether to (a) re-pull `qwen3-vl:latest` so the
branch stays live, (b) patch `production_wiring.py` to fail fast at config load with a clear error
when `PILLSAFE_STAGE1=ollama` is set and the tag is absent, or (c) leave it as documented, accepted
debt (this entry is then the warning a future incident responder needs). No action taken by the SA.

**Owning doc:** `Production\PillSafe\dev\brains\production_wiring.py` (`build_reader()`, the
`PILLSAFE_STAGE1=ollama` branch) · Ollama local model store (`qwen3-vl:latest` removal, 2026-08-15).

---

## Active roadmap — pointers only, not copies

The short-imprint false-accept mitigation design (two switchable flags: withhold imprint credit
on a low-confidence face-presence read, and cap credit on an uncorroborated short exact match) is
**designed and measured, not yet shipped** — it is scheduled to land with the same "2.6 bundle"
release as item 9 above. → `NB08_Notebook/specs/NB08_Identification.md` §3.17.13.8 owns the design
and every number.

The colour-scoring fix (the colour channel currently reports how confident the classifier is, not
whether the colour actually matches) is likewise **designed and measured, not yet shipped**, and
lands in the same bundle. → `NB08_Notebook/specs/NB08_Identification.md` §3.17.15 owns the design
and every number. 🔴 **It also tightened item 9 above**: the threshold guard that bundle needs is
stricter than item 9 states once the corroboration cap is switched on — item 9's own figure is the
guard for the *other* mechanism, not for this one. Read §3.17.15 before implementing either guard.

The shape-channel disposition (766 formulary reference rows carry no shape at all; the shape
channel's pre-existing 0.5 neutral for a blank reference is the same kind of defect the colour fix
above corrects, applying the same fix) is likewise **designed and measured, not yet shipped**, and
lands in the same bundle. Zero of the 11 supported DINs are affected, and the fix was found
structurally unreachable in the current held-out population (see item 10 above). →
`NB08_Notebook/specs/NB08_Identification.md` §3.17.16 owns the characterisation, the design and
every number.

**Scorer warm-on-signin (filed 2026-08-15, Muthu decision D-11 in the MPR1 session).** The NF4
scorer load intermittently dies with an access violation when triggered lazily on a uvicorn worker
thread at the first request — measured 2026-08-15 (1 of 3 starts crashed; standalone main-thread
loads 4/4 clean; evidence `NB08_Notebook/results/nb08_tray_route/run3/` + the MPR1-T03 report's
B3/B4 section). Production keeps the lazy load FOR NOW (Muthu's explicit call — no warm-at-boot,
no idle 3.1 GB hold). The chosen design: **warm the scorer when a user SIGNS IN on mypillsafe** —
the sign-in event fires a fire-and-forget warm-up call to the sidecar (new lightweight
`/warmup` or equivalent), so the model is resident on the main-thread-safe path minutes before the
first scan can arrive. Until built, the first scan after a sidecar restart carries the measured
intermittent crash risk, and the interactive-only scheduled task will NOT auto-restart a crashed
process. Dev already mitigates via `NB08_Notebook/src/nb08_tray_devserver.py` (main-thread warm
before serving) — reuse its ordering when implementing.

**Deboss-only pills vs the frozen margin gate — tray flow (filed 2026-08-15, MPR1 run5/run6).**
On the multi-pill tray route, 9 of the 11 supported OTC pills verify on the no-flash burned frames
(0 false accepts across every run). The two misses are the deboss-only pills: senekot.s ("S S")
and dulcolax ("D"). Muthu ordered a flash-arm (P2) evidence run; **the flash-rescue prediction was
REFUTED**: dulcolax never reaches a read (presence NONE), and senekot.s reads its own name
correctly at margin 8.474 against the frozen 8.5949 gate — 1.4% short, with the landed Sample17
M0 crop on the same well/arm scoring 8.835, i.e. the pill sits ON the frozen boundary (dulcolax's
landed evidence: 0 ungated in 7 appearances, best 3.73). This is a **deboss-vs-gate margin
problem, not a capture-arm choice**. The three levers, all outside the MPR1 session's authority:
(1) re-derive the margin threshold on non-burned data; (2) a Stage-2 reader with more relief
sensitivity; (3) a raking-light capture geometry for deboss imprints. Until one lands, the tray
flow's honest behavior for these two pills is abstain/reject with the pharmacist message — never
a false accept. Evidence: `NB08_Notebook/results/nb08_tray_route/run5/` + `run6/` and the
MPR1-T14 report (`NB08_Notebook/orc/MPR1/`).

For everything else currently in flight, the live roadmap and its status live in
`NB08_Notebook/NB08_STATE.md` §5 (timeline) and `NB08_Notebook/specs/NB08_DataModel_v3.md` §4 (work
order) — this file does not duplicate either.
