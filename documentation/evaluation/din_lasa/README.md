# DIN look-alike (LASA) gate — measurement, 2026-07-30

What this folder measures: whether the app can still let a user silently link
a prescription to the **wrong** Drug Identification Number when two product
names look alike.

| File | What it is |
|---|---|
| `lasa_cases.json` | The 22-case regression set. Expectations were fixed **before** the probe ran, from product reasoning rather than from measurement. |
| `probe_lasa.py` | Re-runnable end-to-end probe. Imports the shipped rule and calls the live sidecar endpoint. |
| `results_lasa.json` | Output of the run reported below. |

Re-run it (the brains sidecar must be up — it is laptop-only, in no image and
no compose file):

```
cd dev/brains  && .venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
cd dev/backend && venv/Scripts/python.exe ../../documentation/evaluation/din_lasa/probe_lasa.py
```

---

## The finding: this was never a threshold problem

`dev/brains/app.py` sets `SEARCH_SCORE_CUTOFF = 75.0`, chosen 2026-07-29 by a
sweep of 4 scorers × 9 cutoffs. It takes absent-medication queries from 0/21
to 19/21 correctly returning empty. Two negatives survive it, and the ADR had
recorded them as pairs that "no threshold separates":

| Label query | Best candidate | Score | What differs |
|---|---|---:|---|
| `ZOLTIRAX` | ZOVIRAX | 80.0 | invented name vs a real antiviral |
| `TYLENOL PM EXTRA` | TYLENOL EXTRA STRENGTH | **100.0** | PM contains diphenhydramine; the other does not |

**That 100.0 is the point, and it corrects the ADR's recorded 89.7.**
rapidfuzz's `token_set_ratio` compares the *intersection* of the two token
sets, so a query that is a strict **superset** of a product name scores the
maximum — exactly what an identical match scores. There is no gap left to cut
in. Raising the cutoff cannot reach this pair at any value, and the values
high enough to catch ZOLTIRAX destroy `METFORMIN → APO-METFORMIN` (81.8).

What separates them is not how similar the strings are, but **which of the
label's own words got lost**:

```
METFORMIN        -> SANDOZ METFORMIN FC       every label word kept   -> safe
GRAVOL TABLETS   -> GRAVOL SUPPOSITORIES      every label word kept   -> safe
ZOLTIRAX         -> ZOVIRAX                   lost "ZOLTIRAX"         -> LASA
TYLENOL PM EXTRA -> TYLENOL EXTRA STRENGTH    lost "PM"               -> LASA
```

The rule (`dev/backend/app/services/lasa.py`) is therefore: **over the top-5
candidates, does any one of them contain every significant word the label
printed?** If none does, every option on offer has dropped something the label
said, and the UI stops offering one-tap Confirm. **Zero new tunable numbers.**

### The near-miss inside the rule itself

`rx_guardrails.value_supported_by_label` uses a `_MIN_TOKEN_LEN = 3`
significance filter, and reusing it here would have been the obvious move. It
silently drops **`PM`** — and passes TYLENOL PM EXTRA as an exact match.

The short tokens in Canadian OTC naming are the ones that change what is in
the pill: **PM, ES, XL, SR, XR, CD, DS, HP**. `lasa.label_tokens` therefore
uses a minimum length of **1**, and excludes noise **by meaning instead** —
digit-only tokens and measurement words (`MG`, `ML`, `IU`, …), which describe
the strength, not the medicine. Strength is separately ranked on and is
displayed beside every candidate, so a strength difference is *visible* to the
user in a way a lost word is not. `test_the_min_token_length_that_would_blind_the_rule`
guards this.

---

## Results

**Regression set: 22/22 as expected.** Both documented LASA survivors gate
(`missing=['ZOLTIRAX']`, `missing=['PM']`); all 8 absent/noise queries still
return empty at the cutoff; all 12 real marketed products stay one-tap,
including the generic→branded-generic case the rule most risked breaking.

**False-fire rate** — how often the gate fires on a label naming a product
that genuinely exists (seed 42, drawn from the 11,609-DIN profile tier):

| Arm | n | gated | rate |
|---|---:|---:|---:|
| Exact reference brands used verbatim as the label | 500 | 4 | **0.8 %** |
| Generic-name-only labels (manufacturer prefix dropped) | 200 | 6 | **3.0 %** |

## Honest provenance — read before quoting any of this

- **The two LASA pairs are not held out.** The rule was designed by inspecting
  exactly those two pairs. Their pass is a construction check, not evidence of
  generalization. The **false-fire rates are the fresh measurement** — those
  brands were never looked at while the rule was being written.
- **The original WP1 sweep script (62 positives / 21 negatives) is not in the
  repo**; only the cutoff constant's comment survives. This set does not
  reproduce it and does not claim to. The 8 absent-query cases here are the
  subset preserved in `dev/brains/tests/test_reference_endpoints.py`.
- **A defect in this probe's first version, recorded because it nearly became a
  published false result.** The first run sent *raw* label text to the sidecar,
  but the app never does — `brains_client.search_reference` strips strength and
  form first. Raw `DIGOXIN 0.125 MG` returns **nothing** (the extra tokens drag
  the score under 75.0) while cleaned `DIGOXIN` returns digoxin products. The
  probe would have published a failure for a real, marketed,
  narrow-therapeutic-index drug — and would also have *under*-reported gating,
  since raw `ZOLTIRAX 200 MG` likewise falls to empty instead of surfacing
  ZOVIRAX. `probe_lasa.search()` now calls `clean_search_query`, and says why.

## Limits of the rule, stated

1. **One-directional.** It detects label → candidate information *loss*, not
   candidate over-specificity: a label reading only `ADVIL` treats
   `ADVIL COLD AND SINUS` as covered, because the label gave no word to lose.
   That direction is governed by the rule that has always applied — nothing is
   auto-picked, and the user reads the full product name before tapping.
2. **It never filters or blocks.** Near-miss candidates are still shown and
   still linkable. Hiding them would block recovery from OCR noise, and DIN
   linking is deliberately offered rather than mandatory: a *wrong* DIN feeds
   SB2 a wrong appearance row and BB3 a wrong monograph, which is worse than
   no DIN at all.
3. **Stale annotation on an edited name.** Editing the medication name on the
   review card does not re-annotate the suggestions fetched at scan time;
   "pick a different one" re-searches and re-annotates. Known, not fixed.
4. **The manufacturer tier is a judgement call, not a measurement.** A label
   reading `APO-METFORMIN` against a `TEVA METFORMIN` row is a real difference
   — different DIN, different pill, so SB2 would reject a correct photo — but
   not a wrong-medicine risk. It gets a softer notice, because firing the
   look-alike alarm on most Canadian generics would train users to dismiss it.
