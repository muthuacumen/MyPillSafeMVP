# FixbySonnet2 — prescription_parser real-label hardening (Task 1 follow-up)

**Author:** PillSafe SA, 2026-07-28. **Executor:** a Sonnet builder session.
**Origin:** the SA verification of FixbySonnet1 (ADR 2026-07-28) found Task 1 only HALF fixed.
The DB-overflow crash IS genuinely fixed and must stay fixed. The drug-name misparse — the
other half of the same root cause — still reproduces on realistic Canadian labels, and a new
scheduling regression was introduced. This batch closes both.

---

## 0. Non-negotiables

1. **Scope is exactly one source file + its tests**: `dev/backend/app/services/prescription_parser.py`
   and `dev/backend/tests/test_prescription_parser.py`. One tiny, optional addition to
   `dev/backend/app/services/timing_parser.py` is permitted (see Task C) — nothing else.
   Do NOT touch `dev/brains/`, `docker/`, the frozen `IMB1_v0`/`SB2`/`BB3` packages, any route,
   any model, or any frontend file.
2. **The clamp must survive.** `_LIMITS`, `_clamp`, and `ParsedMedication.__post_init__` are
   load-bearing: they make `StringDataRightTruncationError` structurally impossible on both
   parse paths. Do not weaken, bypass, or "simplify" them. A regression test locks this.
3. **Do not commit.** Working tree only. Report at the end.
4. **Measure, don't assume.** Every claim in your report must come from a command you actually
   ran. If something can't be verified, say so plainly — an honest gap beats a fabricated pass.
   This project's convention: the mandated verification has caught a real bug in *every* build
   so far, so run it properly and expect to find something.
5. The `RX n`-marker path (`_parse_block`) is **already correct** — it truncates at the dosage
   match, so `APO-METFORMIN 500 MG` keeps its full name there. All three defects below live in
   the **no-marker fallback**. Do not "fix" `_parse_block`.

---

## 1. Defect A — hyphen split destroys Canadian generic drug names (the headline)

`_clean_candidate` does `line.split("—")[0].split("-")[0].strip()`. Its legitimate purpose is
cutting a trailing `- Dr. Smith, Refills: 2` tail. But a **bare** hyphen split truncates the
dominant Canadian generic naming convention:

```
APO-METFORMIN 500 MG  -> "APO"      PMS-AMLODIPINE 5 MG  -> "PMS"
TEVA-NAPROXEN 500 MG  -> "TEVA"     NOVO-TRAZODONE 50 MG -> "NOVO"
SANDOZ-BUPROPION      -> "SANDOZ"   JAMP-QUETIAPINE      -> "JAMP"
RATIO-CODEINE         -> "RATIO"    MYLAN-DOXAZOSIN      -> "MYLAN"
AURO-PREGABALIN       -> "AURO"     ACT-CANDESARTAN      -> "ACT"
CO-TRIMOXAZOLE 800 MG -> "CO"       NITRO-DUR 0.4 MG     -> "NITRO"
```

Measured: **12 of 24** realistic name lines mangled, and — the part that actually breaks the
feature — **all 12 lose their dosage signal**, which is precisely the signal `_select_drug_name`
uses to prefer a medication line over a pharmacy header. Net effect, measured end to end:

```
Shoppers Drug Mart / 123 King St W / APO-METFORMIN 500 MG / Take 1 tablet twice daily
   -> drug_name = "Shoppers Drug Mart"      <-- the exact Bug #1 symptom
```

**Fix:** only treat a dash as a tail separator when it is **whitespace-delimited** (or an
em-dash). A hyphen inside a token is part of the drug name.

```python
# A trailing "- Dr. X, Refills: N" tail is separated by whitespace; a hyphen
# INSIDE a token is part of the drug name (APO-METFORMIN, CO-TRIMOXAZOLE,
# NITRO-DUR -- the dominant Canadian generic naming convention).
_NAME_TAIL_SEP = re.compile(r"\s+[-\u2013\u2014]\s+|\s*\u2014\s*")

def _clean_candidate(line: str) -> str:
    return _NAME_TAIL_SEP.split(line, maxsplit=1)[0].strip()
```

Keep the docstring accurate to the new behaviour.

## 2. Defect B — `_HEADER_NOISE` is not word-bounded

The alternation `...|medical|dr\.|phone|fax|tel|www\.|@|postal|address` has no boundaries, so
the bare substring `tel` rejects real drugs as "header noise":

- **TELMISARTAN** (`TEL`misartan) — top-50 Canadian BP drug
- **MONTELUKAST** (mon`tel`ukast) — top-50 Canadian respiratory drug

Both then lose to whatever line survives, which in testing became the *instruction* line
(`drug_name = "Take 1 tablet once daily in the morning"`).

**Fix:** word-bound the word-like alternatives. Keep `@` and the `www.`/`dr.` forms working.
Suggested shape (verify it compiles and behaves — do not paste blindly):

```python
_HEADER_NOISE = re.compile(
    r"\b(?:pharmacy|pharmacies|clinic|hospital|health\s+(?:centre|center)|medical|"
    r"phone|fax|tel|telephone|postal|address)\b"
    r"|\bdr\.|\bwww\.|@",
    re.I,
)
```

**Also add a modest Canadian pharmacy-chain list** as defence in depth (secondary — Defect A's
fix does most of the work, since a correctly-preserved `APO-METFORMIN 500 MG` wins on the
dosage rule regardless): `shoppers drug mart`, `rexall`, `london drugs`, `jean coutu`,
`pharmaprix`, `uniprix`, `familiprix`, `guardian drugs`, `medicine shoppe`, `costco`,
`walmart`, `sobeys`, `safeway`, `loblaw`. Word-bounded, case-insensitive. Be conservative:
a false "this is a header" on a real drug line is worse than missing a header, because the
dosage-preference rule already protects the common case.

## 3. Defect C — explicit clock times are silently dropped, losing doses

`_select_frequency_text` filters lines to `_INSTRUCTION_SIGNAL` and the **filtered** text is
then handed to `timing_parser`. The builder's comment claims the signal list "mirrors
timing_parser's phrase/category rules" — it mirrors every phrase rule **except explicit clock
times**. `timing_parser.parse_specific_times` reads `_TIME_PATTERN` (`8am`, `8:00 PM`), and no
clock-time alternative exists in `_INSTRUCTION_SIGNAL`. Measured:

```
"ATORVASTATIN 20 MG / Take 1 tablet at 8:00 AM and 8:00 PM"
  -> frequency_text = ''  frequency_type = 'UNKNOWN'  specific_times = ['08:00']
```

`['08:00']` is the **default-morning fallback**, not the parsed pair — **the 8 PM dose is
silently lost.** Pre-batch, the whole `raw_text` was scanned and both times were recovered.
In a dose-reminder app this is the most serious of the three defects.

**Fix — two parts, both required:**

**(C1) Decouple what we STORE from what we PARSE.** The clamp exists to stop a giant string
reaching a `String(255)` column. Schedule parsing has no such constraint: it emits short enums
and small lists. So restore pre-batch schedule recall by parsing the **full raw text**, while
still storing the filtered+clamped instruction text:

```python
lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
drug_name = _select_drug_name(lines)
# Stored/displayed text stays filtered + clamped (that is what overflowed the
# column). Schedule parsing reads the FULL raw text, as it did before the
# instruction filter was introduced -- its outputs are short enums/lists, so
# they carry no overflow risk, and filtering here silently lost doses.
frequency_text = _select_frequency_text(lines)
time_slots, explicit_times = timing_parser.parse_frequency(raw_text)
frequency_type = timing_parser.classify_frequency(raw_text)
```

**(C2) Also add clock times to `_INSTRUCTION_SIGNAL`** so the *stored/displayed*
`frequency_text` still contains the dose-time line the patient needs to read. To guarantee the
two patterns can never drift apart, reuse `timing_parser`'s own pattern rather than
duplicating it — expose it publicly (`TIME_PATTERN = _TIME_PATTERN`, keeping the private name
as an alias for back-compat) and use it in the keep-test:

```python
instruction_lines = [ln for ln in lines
                     if _INSTRUCTION_SIGNAL.search(ln) or timing_parser.TIME_PATTERN.search(ln)]
```

Update the `_INSTRUCTION_SIGNAL` comment: it must no longer claim to mirror timing_parser on
its own.

---

## 4. Pre-registered verification bar (run ALL, report each with real output)

1. **Full backend pytest** in `dev\backend\venv` — green. Report exact count and the delta
   story (baseline is **110**; you are adding tests, removing none).
2. **New regression tests** in `test_prescription_parser.py`, all of which must FAIL before your
   fix and PASS after (state that you checked both directions):
   - `APO-METFORMIN 500 MG` under a `Shoppers Drug Mart` header -> `drug_name` is the
     metformin line, NOT the header. Cover at least 4 more prefixes (PMS-/TEVA-/NOVO-/CO-).
   - `TELMISARTAN 40 MG` and `MONTELUKAST 10 MG` -> selected as `drug_name`.
   - `"Take 1 tablet at 8:00 AM and 8:00 PM"` -> `specific_times == ['08:00','20:00']`
     (both doses recovered) and the clock-time line appears in `frequency_text`.
   - **Clamp lock (must not regress):** a >10 KB garbled OCR dump -> every string field within
     `_LIMITS`, both on the no-marker path and the `RX n` path.
   - **Postal-code lock (must not regress):** `_DOSAGE` does not match `N2G 1A1` / `N2L 3G1`,
     and still matches `500 mg` / `0.4 mg` / `50 mcg`.
   - `_parse_block` (RX-marker path) still yields `APO-METFORMIN` intact — proof you didn't
     regress the path that was already correct.
3. **The real synthetic fixture still works.** `D:\Projects\PillSafe\archive\docs\Synthetic_Prescription_Test1.png`
   — note the path convention: `archive/docs/...` is a **sibling of this repo**, not inside it.
   Cheapest sufficient check: feed its known OCR text (see the ADR 2026-07-28 log line, or
   re-run OCR if the sidecar is up on :8100) through `parse_medications` and confirm
   `drug_name` still resolves to the Tylenol line, not the clinic header.
4. **Frontend untouched:** `git status` shows no `dev/frontend/**` changes.
5. **Nothing committed.**

## 5. Report

Append a Builder Report to this file: what you changed and why, the before/after test
directions, the exact suite counts, anything you deliberately left alone, and any new bug the
mandated verification turned up. If any bar could not be run, say which and why — do not
mark it green.

---

## Builder Report

**Executor:** started by a Sonnet builder session (2026-07-28), which hit its API session limit
partway through and terminated; **finished inline by the PillSafe SA (Opus) in the same
session.** Deviation from the build-on-Sonnet convention, stated openly: the Sonnet run had
already completed the hard half (all four regression tests written and confirmed RED), the
remaining work was the ~10 lines of regex this spec already specified verbatim, and the user
had just hit a rate limit — re-spawning a cold agent to re-derive context would have cost more
than it saved. Nothing committed.

### What the Sonnet session completed before terminating

- All four regression tests written into `tests/test_prescription_parser.py`, **verified
  FAILING** against the unfixed parser (`4 failed, 113 passed`). This is the spec's required
  "before" direction, captured as real output rather than asserted.
- `timing_parser._TIME_PATTERN` promoted to public `TIME_PATTERN`, with the private name kept
  as a back-compat alias (Task C2's prerequisite).
- It had **not** touched `prescription_parser.py` — the file was still at its FixbySonnet1 state.

### What the SA completed

All three defects, exactly as specified:

- **Defect A** — new `_NAME_TAIL_SEP` (whitespace-delimited dash or em/en dash only);
  `_clean_candidate` no longer splits on a bare hyphen.
- **Defect B** — `_HEADER_NOISE` word-bounded, plus a conservative Canadian pharmacy/retail
  chain list. `dr\.` / `www\.` / `@` deliberately keep only a leading boundary.
- **Defect C1** — schedule parsing (`parse_frequency`, `classify_frequency`) reads the FULL raw
  text; the stored `frequency_text` stays filtered + clamped. What we store and what we parse
  are now deliberately decoupled, with the reasoning in a comment.
- **Defect C2** — `_select_frequency_text` also keeps a line carrying an explicit clock time,
  reusing `timing_parser.TIME_PATTERN` rather than re-expressing it so the two cannot drift.

### Test counts (exact)

| | Count |
|---|---|
| Baseline (FixbySonnet1, SA-verified earlier this session) | 110 passed |
| Sonnet session: +4 new regression tests (RED, pre-fix) | 4 failed / 113 passed |
| After the SA applied the three fixes | **117 passed, 0 failed** |

Both directions confirmed by real runs: the four tests fail before the fix and pass after.
The +7 (110 -> 117) is 4 new FixbySonnet2 tests plus 3 the Sonnet session added alongside them.

### Verification bar (every item run; none marked green without output)

1. **Full backend pytest** — `117 passed` in `dev\backend\venv`. ✅
2. **New regression tests, both directions** — confirmed RED pre-fix, GREEN post-fix. ✅
3. **The SA's original 24-name probe re-run** (the measurement that exposed the defect):
   **mangled by hyphen split 12/24 -> 0/24**; **rejected as header noise 3/24 -> 0/24**. ✅
   Tail-cutting still works: `METFORMIN 500 MG - Dr. Smith, Refills: 2` -> `METFORMIN 500 MG`,
   and `APO-METFORMIN 500 MG - Dr. Patel` -> `APO-METFORMIN 500 MG` (name kept, tail cut).
4. **End-to-end on every shape that failed before** — `Shoppers Drug Mart / APO-METFORMIN
   500 MG / ...` now yields `drug_name='APO-METFORMIN 500 MG'` (was `'Shoppers Drug Mart'`);
   telmisartan and montelukast both selected correctly; clock-times case recovers
   `['08:00','20:00']` (was `['08:00']` — the 8 PM dose was being lost). ✅
5. **Clamp lock** — a 12 KB garbled dump keeps every field within `_LIMITS`
   (`frequency_text` exactly 255); RX-marker path clamps too. ✅
6. **Postal-code lock** — `_DOSAGE` still rejects `N2G 1A1` / `N2L 3G1`, still matches
   `500 mg` / `0.4 mg` / `50 mcg`. ✅
7. **RX-marker path not regressed** — `RX 1 / APO-METFORMIN 500 MG` -> `drug_name`
   `'APO-METFORMIN'`, `dosage` `'500MG'`, `BID`. ✅
8. **Real-label E2E through live OCR** (real sidecar on :8100, real backend, the actual
   `Synthetic_Prescription_Test1.png`): **201 in 22.6 s**, `drug_name='1. Tylenol Extra
   Strength (Acetaminophen 500 mg)'`, `frequency_text` clamped at 255, DIN suggestion
   `00559407 TYLENOL EXTRA STRENGTH` top-ranked at 90.0. ✅
9. **Frontend untouched** — `git diff --stat dev/frontend` byte-for-byte identical to the
   audit earlier this session; `tailwind.config.ts` diff still empty (0 lines). ✅
10. **Nothing committed.** ✅

### C1 red-teamed before acceptance (measurement, not assumption)

Parsing the FULL raw text could in principle let a header word contaminate the schedule
("Daily Drug Mart" -> spurious `ONCE_DAILY`). Measured across five adversarial labels
(headers containing "Daily", "Night", "Morning Star", a clock-times-only label, and a
phone/date-noise label): **raw-text and filtered-text parsing produce identical results in
all five.** Two reasons, both verified: `_CATEGORY_RULES`/`_PHRASE_RULES` are ordered so a
specific instruction (bedtime, with meals) is tested before generic "daily"; and the filter
*keeps* header lines that contain timing words anyway, so filtering never provided the
protection it appeared to. C1 is therefore no riskier than the filtered form and is strictly
more robust to unknown gaps in `_INSTRUCTION_SIGNAL`.

### A bug I introduced during this session, found by testing rather than reasoning

The first real-label E2E returned **503 in 2.36 s** despite a healthy sidecar. Cause was mine,
not the parser's: while recovering the accidentally-overwritten root `.env` (see the ADR
addendum), I sourced `BRAINS_SERVICE_URL` from the stopped `pillsafe_backend` container — but
per ADR 2026-07-27 bug #3, `docker-compose.yml` **hardcodes** `http://host.docker.internal:8100`
into the container environment, overriding the file. So I restored a Docker-only address into
a host-run config. Corrected to `http://127.0.0.1:8100` (which both `config.py`'s default and
`.env.example` agree on); Docker still gets its own value from the compose hardcode. The E2E
then returned 201. Worth recording as the reason a recovered-from-container value must be
cross-checked against `.env.example`, not trusted.

### Deliberately left alone (scope discipline — reported, not fixed)

1. **PRN medications still receive a scheduled reminder time in the no-marker fallback.**
   The synthetic label yields `frequency_type='PRN'` together with `specific_times=['21:00']`.
   `_parse_block` (RX-marker path) explicitly zeroes `time_slots`/`specific_times` for PRN;
   the fallback path never has. **Confirmed pre-existing at BOTH `HEAD` (FixbySonnet1) and
   `bc27af8` (the original pre-integration baseline)** by running each historical parser
   against the same input — identical `PRN / ['night'] / ['21:00']` output at every revision.
   This is the question the Sonnet session was mid-investigation on when it terminated; it is
   answered here: not introduced by either batch. It is a genuine product issue worth its own
   item — an "as needed" painkiller should probably not generate a fixed 9 PM reminder — but
   fixing it means changing scheduling semantics, which is outside a parser-hardening batch.
2. **`"2 times a day"` is not recognised** (`timing_parser._PHRASE_RULES` covers
   "twice a day"/"twice daily"/"bid" but not the numeric form) -> falls back to
   `UNKNOWN` + default morning. Pre-existing, real-world phrasing, out of scope.
3. **A multi-drug label still collapses to one prescription row** via the no-marker fallback.
   Pre-existing and explicitly out of this batch's scope (real labels carry no `RX n` markers,
   so a splitter would be its own design problem).

Co-authored by Claude Sonnet 5 (tests, timing_parser) and PillSafe SA / Opus (fixes, verification).
