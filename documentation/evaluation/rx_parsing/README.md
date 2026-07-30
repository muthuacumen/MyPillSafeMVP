# Prescription Scanning: Measured Limitations

**What this folder is.** The complete experiment record behind MyPillSafe's prescription-label
parsing: the 24 evaluation labels and their expected answers, every system's raw output, and how
to re-run the whole thing. Nothing here is estimated, projected, or rounded up.

**Reporting rule for this document.** Counts, never percentages — the evaluation set is 24 labels
and a percentage would imply a precision it cannot support. This document does not claim "100%
accuracy" for anything; the honest form of a perfect run is "12/12 labels, 50/50 fields on this
evaluation set."

| file | what it is |
|---|---|
| `labels_and_ground_truth.json` | all 24 labels + expected answers, exported from the harness |
| `results_three_way.json` | the current three-system comparison (regex / qwen2.5:7b / Haiku 4.5), 3 runs each |
| `results_via_service.json` | the shipped pipeline's own acceptance run (sidecar + guardrails + derivation), 3 runs — **pre-G6**, retained because it is the record of the label-C defect |
| `results_via_service_2026-07-30_postfix_G6.json` | the same run after the G6 as-needed guard shipped, 3 runs — see §5.1 |
| `results_*_2026-07-28_prewidening.json` | the superseded 2026-07-28 runs, kept so the change in numbers is inspectable rather than asserted |
| `harness_pointer.md` | how to reproduce both runs |

**Scoring changed on 2026-07-29, and the numbers below moved because of it.** Until that date the
*original 12* were scored on medication count + name fragments only — blind to whether the
frequency, the dosage, or the reminder times were right. They now carry per-field truths
(20 medications × 4 fields = **80 newly scored fields**, 50 → **130** overall), authored from each
label's own text and reviewed with zero corrections. Nothing about any system changed; the
measurement got sharper, and it found things. Those findings are reported here as findings — the
earlier, more flattering numbers are preserved in the `_prewidening` files above rather than
quietly replaced.

**Safety events and errors are counted separately.** A *safety event* is a defect in what the
system extracted (a daily reminder on a once-weekly medication, times on an as-needed medication,
a dropped medication). An *error* is the call failing outright — the extraction never happened, so
there is nothing to be wrong about. Both are real production risks and both are counted, but
merging them would report a parsing defect that did not occur.

---

## 1. The two layers, and which one was measured

Scanning a prescription is two problems stacked, and they fail differently:

1. **Optical character recognition (OCR)** — photo → text.
2. **Parsing** — text → structured medications and a schedule.

The measurement in this folder is of **layer 2**. Layer 1's known limits are documented from
this project's own defect history (§2) rather than from a benchmark.

## 2. Layer 1 — OCR: what has actually gone wrong

Every item below is a real defect found on this project and fixed; each is also a reason the
review screen exists.

- **A pharmacy header became the drug name.** A real label's letterhead outranked the medication
  line. (`prescription_parser._select_drug_name`, FixbySonnet1 Task 1.)
- **Canadian generic names were truncated at the hyphen.** `APO-METFORMIN` → `APO`,
  `CO-TRIMOXAZOLE` → `CO`, `NITRO-DUR` → `NITRO` — 12 of 24 realistic names measured, on the
  dominant Canadian naming convention. (FixbySonnet2 Defect A.)
- **A dose was silently lost.** A line carrying only a clock time was filtered out before parsing,
  taking an 8 p.m. dose with it. (FixbySonnet2 Defect C.)
- **A garbled real label crashed the save.** >1,000 characters of noisy OCR text overflowed a
  255-character database column. (FixbySonnet1 Task 1.)
- **OCR is slow without a GPU.** Measured ~2 m 21 s per label on CPU, which is why OCR runs on a
  sidecar host and not on the deployment droplet.
- **Character confusions are routine.** `0`/`O`, `1`/`l`/`I`, `5`/`S`, `8`/`B`, `rn`/`m`. The
  guardrails compare over a fold of exactly these confusions so a correctly-repaired name is not
  mistaken for an invented one.

## 3. Layer 2 — parsing: the measured comparison

**The evaluation set** (`labels_and_ground_truth.json`): 24 labels.

- **The original 12** are the rule-based parser's *own development fixtures* — its home turf. A
  system scoring 12/12 here has demonstrated nothing except that it did not regress.
- **The held-out 12** were authored fresh by the SA for this evaluation and never used to tune any
  parser. They cover the shapes a Canadian label actually takes and the rule-based parser's known
  gaps: once-weekly, every-N-hours, bare "daily", a tapering dose, a split dose, a French Québec
  label, sig codes (`1 TAB PO QD AM`), OCR noise, a half tablet, insulin in units, and an
  unenumerated two-medication label with no strengths.

**"Safety events"** counts outcomes that could harm someone: inventing a medication, missing one,
putting times on an as-needed medication, or — the one this whole work exists to prevent — putting
a **daily reminder on a once-weekly medication**.

### 2026-07-29, three systems, **three runs each**, temperature 0, per-field scoring on all 24 labels

Worst run reported, never the mean: for an intermittent safety error, "it usually does not happen"
is not a claim a medication app gets to make.

| system | original 12 fully correct | original fields | held-out fully correct | held-out fields | **all fields** | safety events | errors | mean latency | cost/call |
|---|---|---|---|---|---|---|---|---|---|
| rule-based regex parser (previous production) | **2/12** | 69/80 | **1/12** | 25/50 | 94/130 | **2** | 0 | ~0 s | 0 |
| **qwen2.5:7b-instruct, local (SELECTED)** | 6/12 | 74/80 | 9/12 | 46/50 | 120/130 | 0 | 0 | 2.78 s | 0 |
| claude-haiku-4-5 (finding only, not wired) | 12/12 | 80/80 | 12/12 | 50/50 | **130/130** | 0 | 0 | 1.31 s | ~0.13¢ |

All three systems still find every medication on the original 12 (12/12 by the old count+name
measure). What the widening shows is that finding the medication was never the hard part.

The rule-based parser's two safety events were a daily reminder generated for a once-weekly
alendronate label, and a missed medication. Both reproduced in all three runs.

**The widening's main finding: qwen's twice-daily arithmetic is systematically wrong, not
occasionally wrong.** Every one of qwen's six lost original-12 fields is the same defect — a `BID`
medication given `08:00 + 13:00` instead of `08:00 + 18:00` — on labels B, C, D, E, J and L. This
document previously described that error as qwen's *single* held-out miss and attributed it to the
French Québec label. It is neither single nor French-specific: the old scoring simply could not see
it on the original 12. The design response in §4 was already the right one; the defect it defends
against is seven times more common than the record showed.

qwen's remaining held-out losses are all previously documented cases: the prednisone taper
classified `EVERY_N_HOURS` instead of `TAPER`, the split-dose label, and the French twice-daily
label. Held-out 9/12 is the honest worst-case reading of known misses, not new breakage.

**Run-to-run stability over three runs** (comparing what each system actually emitted, not merely
whether it scored well):

| system | labels differing across 3 runs | what differed |
|---|---|---|
| rule-based regex parser | 0/24 | — (deterministic by construction) |
| qwen2.5:7b-instruct | 1/24 | label A, Tylenol "q6h PRN": `PRN` in one run, `EVERY_N_HOURS` in two. Both are accepted answers and both carry no reminder time, so it scores clean either way — but it is a genuine frequency-category flip at temperature 0 |
| claude-haiku-4-5 | 1/24 | H6: `APO-METFORMIN 500 MG TABLET` vs `APO-METFORMIN 500 MG`. A trailing token; no semantic difference |

Neither model is bit-stable at temperature 0, and the larger model is not exempt — it is merely
cosmetic in its instability where the 7B is semantic.

### The model finding, stated honestly

> Claude Haiku 4.5 measured 12/12 labels fully correct (50/50 fields, 0 safety events) on this
> evaluation; a more powerful cloud LLM is expected to perform at least as well. The capstone
> deliberately selects the local qwen2.5:7b for self-containment and zero cloud cost; the proposer
> is swappable by config.

The swap is one setting (`RX_PARSE_BACKEND`), not a redesign.

## 4. What the measurement changed in the design

qwen2.5:7b's losses are **not** extraction failures. It reads the labels correctly — including the
French Québec one, losartan, 50 mg, twice a day — and then does the arithmetic wrong, proposing
08:00 and 13:00 for a twice-daily schedule instead of 08:00 and 18:00. The per-field scoring added
on 2026-07-29 showed this happening on **seven of the twenty-four labels**, always the same wrong
pair. When this section was first written only the French one was visible, and the design decision
below was made on that single observation. The wider measurement did not change the decision — it
raised how much the decision was worth.

So the model is no longer asked. It returns only what the label *says*, including any clock time
literally printed on it; reminder times are computed afterwards from a fixed table
(`app/services/rx_guardrails.py: FREQUENCY_TIMES`) that the app owns. That converts a probabilistic
weakness into a structural impossibility, and it applies identically whichever proposer ran.

Five deterministic guards run on every proposal, from either proposer (transplanted from MEDIC,
*Nature Medicine* 2024): catalog cross-check, no-invention, schema, no-silent-defaults, and
conflict detection. The no-invention guard is deliberately **asymmetric**: a time that is not
printed on the label is removed (the fixed table supplies a correct one anyway), but a name or
strength that cannot be matched is **kept and flagged**, never deleted — deleting it would destroy
the model's OCR-repair work on exactly the noisy labels it was chosen to handle, and hand an older
user a blank field to retype from a label they may struggle to read.

## 5. The shipped pipeline's own acceptance run

The comparison above measures *models*. This measures **the application**: the same 24 labels sent
through the real sidecar endpoint, the real guardrails, and the real server-side time derivation
(`redteam_llm_extraction.py --via-service`, results in `results_via_service.json`).

| | original 12 fully correct | original fields | held-out fully correct | held-out fields | all fields | safety events | errors | WEEKLY/PRN with a reminder time | mean latency |
|---|---|---|---|---|---|---|---|---|---|
| shipped path (qwen + guardrails + derivation) | 9/12 | 76/80 | 11/12 | 49/50 | **125/130** | **1** | 0 | **0** | 2.75 s |

**The derivation layer works.** The shipped path beats the raw model it is built on — 125/130
fields against qwen's 120/130, 9/12 against 6/12 on the original labels — because every one of the
`BID → 08:00 + 13:00` errors in §3 is overwritten by the fixed timing table. The French
twice-daily label that the raw model got wrong scores correctly, by construction. Identical across
all three runs: 0/24 labels differed.

### The one safety event, and why it matters more than the score

> **On label C, the shipped path puts a fixed 9 p.m. daily reminder on an as-needed medication.**
> The label reads `TEVA-NAPROXEN 500 MG — Take 1 tablet at bedtime as needed for pain`. The
> pipeline emits `frequency = BEDTIME`, `times = ['21:00']`. The words "as needed" are dropped, and
> nothing is flagged. Reproduced in **all three runs**.

Three things about this are worth stating plainly, because each one corrects something previously
believed:

1. **~~The model is not the cause.~~ CORRECTED 2026-07-30 — the classification comes from the model,
   and this arm never measured the shipped one.** The claim above rested on the qwen arm of §3
   returning `PRN`. But that arm uses `redteam_llm_extraction.PROMPT`, and the **sidecar uses a
   different prompt** (`dev/brains/rx_extract.py`: the slot→time derivation block removed,
   `specific_times` renamed to `explicit_times`). Called directly, the *shipped* sidecar prompt
   returns `frequency_type = BEDTIME` — so the misclassification is the proposer's, and `rx_guardrails`
   G4 was doing exactly its job when it looked up `BEDTIME → ['21:00']`.
   **The consequence is bigger than the attribution: the §3 qwen arm is not a measurement of the
   shipped proposer**, and cannot be read as one wherever the two prompts diverge.
2. **It was invisible until this scoring change.** Label C is one of the original 12. Under
   count+name scoring it passed — the medication was found and named correctly. Only the frequency
   and times fields expose it. This single case is the return on the whole widening exercise.
3. **The §7 acceptance invariant cannot catch it, and passing is not reassurance.** That check —
   "no WEEKLY or PRN medication may carry a reminder time" — reports **0 offenders**, correctly, in
   all three runs. It reads the pipeline's *own* frequency label, and the pipeline called this
   medication `BEDTIME`. An invariant defined over a system's self-classification is silent by
   construction when the failure *is* the classification. It remains worth keeping; it is simply
   not evidence about this class of error. `redteam_llm_extraction.py` now also computes a
   **truth-side** version of the same bar, from the human-approved `prn` ground-truth field, and
   prints both.

### 5.1 Fixed 2026-07-30 — and what the fix attempt revealed about "temperature 0"

`rx_guardrails` gained **G6**, the only guard that reads the *label* rather than the proposal: if a
medication's own slice of the label text says "as needed" / "prn", no reminder time is derived from
any frequency word or printed clock time, and the medication is flagged `as_needed` +
`needs_schedule`. `frequency_type` is deliberately left as the proposer set it — the label printed
both "at bedtime" *and* "as needed", and both facts are kept. Scoping is per-medication, so
metformin on the same label keeps its `08:00 + 18:00`.

Post-fix acceptance run (`results_via_service_2026-07-30_postfix_G6.json`, 3 runs, live sidecar):

| | original fully correct | original fields | held-out fully correct | held-out fields | all fields | safety events | errors | mean latency |
|---|---|---|---|---|---|---|---|---|
| shipped path + G6 | 8/12 | 75/80 | 11/12 | 49/50 | 124/130 | **0** | 0 | 2.77 s |

**Read that table with the following caveat, which is the session's real finding.**

> **qwen2.5:7b at temperature 0 is stable within a burst of calls and unstable across model loads.**
> Three consecutive calls on label C returned `BEDTIME` 3/3. Forty minutes later, the identical
> prompt and identical text returned `PRN` 3/3. Each burst was internally unanimous; the two bursts
> disagree. A third combination, `PRN` with an **invented** `explicit_times = ["21:00"]` (the label
> prints no clock time), was also observed — caught and stripped by G2 as `not_on_label`.

So the post-fix run **cannot** be read as a demonstration that G6 fixed label C: this session's qwen
did not produce the failing classification, and `124/130` vs `125/130` is that drift, not a
regression — the three changed fields (`A/advil`, `C/naproxen`, `K/acetaminophen`) are all
`frequency_type` values the proposer chose differently, a field G6 never writes. What the run *does*
establish: **zero safety events**, and `as_needed` correctly flagged on label C's naproxen in all
three runs *from the label text*, proving G6 active and correctly scoped.

Proof that G6 handles the failing input lives where it can be made deterministic — the injected-input
unit tests in `dev/backend/tests/test_rx_guardrails.py`, which hand the guards `BEDTIME` on purpose
and are mutation-verified in two directions (disabling G6 fails 5; widening its windows fails exactly
the 2 scoping tests).

**The wider lesson: a 3-run protocol measures burst agreement, not determinism, and systematically
under-reports this model's variance.** The previously recorded "qwen 1/24 nondeterminism, measured
clean" is a within-session number. It follows that no amount of prompt tuning or re-measurement can
retire this error class — which is the argument for a deterministic guard, and the reason the
sidecar prompt was deliberately left unchanged.

## 6. What still fails, and what we do not know

- **A split-dose label loses one of its two times.** "Take 1 tablet in the morning and 2 tablets at
  bedtime" is classified as twice-daily and therefore scheduled 08:00 + 18:00, where the label says
  08:00 + 21:00. This is the shipped path's one held-out miss. The fixed timing table is what makes
  the once-weekly disaster impossible; the same fixedness is what costs this case. The review
  screen is where the user corrects it — which is why the review screen is not optional.
- **An as-needed medication gets a fixed daily reminder.** §5, label C. The most serious open
  defect in this document, in shipped code, and not caused by the model.
- **Neither model is perfectly reproducible at temperature 0.** Over three runs qwen2.5:7b differed
  on 1 of 24 labels (a `PRN` / `EVERY_N_HOURS` flip on an as-needed medication — both accepted, no
  reminder time either way) and Claude Haiku 4.5 differed on 1 of 24 (a trailing `TABLET` token).
  Earlier, re-running the *unchanged* 2026-07-28 harness later that same day, qwen classified the
  prednisone taper as `EVERY_N_HOURS` instead of `TAPER` where it had previously said `TAPER`.
  A 7B model's output is stable enough to build on but not stable enough to *trust*, which is the
  argument for the guardrails and the human confirm, not against them. (Both taper classifications
  are treated identically by the guards: no reminder time, `needs_schedule` flag. The difference is
  a label, not a safety outcome.)
- **One of the ground truths cannot be fully satisfied.** For "twice daily with meals" labels the
  truth accepts either `BID` or `WITH_MEALS` as the frequency, but pins the times to `BID`'s
  canonical `08:00 + 18:00`. The application's fixed timing table maps `WITH_MEALS` to three meal
  times, so whenever the pipeline picks the `WITH_MEALS` branch — an answer the truth explicitly
  permits — it loses the times field automatically (label L, §5). This is a defect in the
  evaluation set, not in the application, and it costs the shipped path one of its three original-12
  misses. Left as measured rather than silently corrected, because the truths were reviewed and
  approved as they stand.
- **The sample is small and self-authored.** 24 labels, written by this project. No real pharmacy
  labels from Canadian chains have been collected or evaluated. That is the honest ceiling on what
  these numbers say.
- **Three runs per system, which is still few.** Enough to catch two stability differences and to
  show that the label-C defect is deterministic rather than intermittent; not enough to bound how
  often a rare flip occurs. An intermittent error absent from three runs has not been shown to be
  absent.
- **A measurement can be wrong in the machine's favour or against it.** An earlier attempt at this
  same run recorded two qwen "safety events" that turned out to be empty responses from a host that
  crashed and rebooted three minutes later — infrastructure, not extraction. They did not reproduce.
  Errors are now counted in their own column for exactly this reason, and the run that produced
  them was discarded rather than published.
- **Reference coverage.** The medication reference now covers **11,609** DINs marketed for human
  use in Canada, of which **7,055** carry the harmonized appearance data a photo check needs. So
  **4,554** real medications — insulin pens, inhalers, creams, eye drops, patches — can be linked
  to a DIN and looked up, but cannot be verified from a photo. The app labels those explicitly
  rather than omitting them. (Before this build the reference held only the 7,055, so those 4,554
  could not be DIN-linked at all.)

## 7. Citations

- Guardrail design (catalog cross-check, halt conditions, abstain-over-generate) — **MEDIC**,
  Amazon Pharmacy: *Large language models for preventing medication direction errors in online
  pharmacies*, **Nature Medicine, 2024**. DOI [10.1038/s41591-024-02933-8](https://www.nature.com/articles/s41591-024-02933-8)
  · open access: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11186789/>
  Reported production results: 33% reduction in near-miss events (CI 26–40%) and 95.1% flagging
  accuracy on historical errors; a 10-shot frontier LLM produced 4.38× *more* near-miss events
  (CI 3.13–6.64) than MEDIC's guarded pipeline. Note that 95.1% is a **flagging** metric — which is
  why this project's no-invention guard flags rather than deletes.
- Few-shot clinical information extraction — Agrawal, Hegselmann, Lang, Kim, Sontag: *Large
  language models are few-shot clinical information extractors*, **EMNLP 2022**, pp. 1998–2022.
  DOI [10.18653/v1/2022.emnlp-main.130](https://aclanthology.org/2022.emnlp-main.130/)
- The rule-based baseline for this task — Xu, Stenner, Doan, Johnson, Waitman, Denny: *MedEx: a
  medication information extraction system for clinical narratives*, **JAMIA 2010;17(1):19–24**,
  PMID [20064797](https://pubmed.ncbi.nlm.nih.gov/20064797/). Reported F-scores: 93.2% drug name,
  94.5% strength, 96.0% frequency.

Verification status for all three is recorded in
`documentation/deployment/LLM_Rx_Parsing_RedTeam_Brief.md` §5.

---

*This disclosure is a Muthu-authorized exception to the project's standing rule against publishing
development-set metrics on public pages: it is honest-limitations content, not a performance claim.
The rule remains in force for IMB1/SB2/BB3 performance numbers.*
