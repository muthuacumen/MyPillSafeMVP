"""Three-way Rx-extraction probe: deterministic regex parser vs qwen2.5:7b-instruct
(local Ollama) vs claude-haiku-4-5 (CB4's production tier).

Answers LLM_Rx_Parsing_RedTeam_Brief.md section 7 Q1 -- the decisive un-measured
number: actual per-field extraction accuracy on Canadian label text.

Two case sets:
  * ORIGINAL 12 (imported from redteam_probe_splitter.py) -- the set the regex
    parser was DEVELOPED against (its home turf; regex is 12/12 here).
    Scored on record count + name fragments, AND (since 2026-07-29) per-field
    exactly like the held-out set -- see ORIGINAL_PERFIELD below. Before that
    widening this arm could not see a frequency, dosage or reminder-time
    error, so the published "0 safety events" was only ever a statement about
    the held-out 12.
  * HELD-OUT 12 (authored fresh in this file, never used to tune the parser) --
    realistic Canadian label shapes incl. the known regex gaps (weekly, every-N
    -hours, bare daily, taper, split-dose, French, sig codes, OCR noise,
    half-tablet, units/insulin, unenumerated no-strength multi-med).
    Scored per-field: count, name, dosage, frequency category, reminder times,
    plus SAFETY EVENTS (phantom med, missed med, times-for-PRN,
    daily-times-for-weekly, dosage/name not present on label).

All three systems play the same game: the prompt gives the LLMs the app's own
slot->time defaults (timing_parser._DEFAULT_SLOT_TIME semantics) so times are
comparable. Ground truth encodes what the APP should store, incl. [] times for
PRN and WEEKLY (a fixed daily reminder for a weekly med is the catastrophic
event this probe exists to expose).

Run with the backend venv:
  dev\\backend\\venv\\Scripts\\python.exe documentation\\deployment\\redteam_llm_extraction.py [--skip-qwen] [--skip-haiku]

Needs: Ollama on 127.0.0.1:11434 with qwen2.5:7b-instruct pulled;
LLM_API_KEY in the repo-root .env (or dev/backend/.env) for the Haiku arm.
Writes: redteam_llm_extraction_perfield_results.json next to this file. The
pre-widening files (redteam_llm_extraction_results.json and its via-service
twin) are the PUBLISHED record of the narrower scoring and are never
overwritten -- the point of the widening is that the headline moved, which is
only auditable if both numbers survive.

`--repeats N` runs every arm N times. qwen2.5:7b at temperature 0 is MEASURED
non-deterministic (6 of 24 labels differed across two runs on one machine), so
a single run cannot honestly claim an intermittent error class is absent. With
N>1 the harness reports per-run numbers, the WORST run as the headline, and
which labels changed answer between runs.

--- FixbyOPUS3 §7: `--via-service` (pre-registered acceptance mode) ---------

  dev\\backend\\venv\\Scripts\\python.exe documentation\\deployment\\redteam_llm_extraction.py --via-service

runs the SAME 24 labels through the REAL shipped path -- the brains sidecar's
POST /rx/extract (local qwen), then `app.services.rx_guardrails`, then the
deterministic server-side time derivation -- instead of calling a model
directly. Needs the sidecar running at BRAINS_SERVICE_URL (default
127.0.0.1:8100) as well as Ollama; a down sidecar is not an error, it is the
regex-fallback path, and the run reports `parse_source` per case so that is
visible rather than silent.

Two things differ from the raw-model arms and are deliberate:
  * the scored `specific_times` are the DERIVED reminder times (the truths in
    HELDOUT_CASES[*]["times"] have always been derived times, e.g. H10
    BEDTIME -> ["21:00"]); the model's own field is now `explicit_times` and
    holds only clock times literally printed on the label;
  * guardrail G1 (reference catalog cross-check) is NOT run here. It only
    ever adds the informational `not_in_reference` flag, affects no scored
    field, and would make the reported latency incomparable with the
    single-call model arms.

Writes: redteam_llm_extraction_via_service_results.json (a SEPARATE file --
the three-way results file is the published experiment record and must not be
overwritten by an acceptance run).

  --export-labels <path>  dumps the 24 labels + ground truths as JSON and
                          exits; this is how
                          documentation/evaluation/rx_parsing/labels_and_ground_truth.json
                          is produced.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "dev" / "backend"))
sys.path.insert(0, str(HERE))

from app.services.prescription_parser import parse_medications  # noqa: E402
from redteam_probe_splitter import CASES as ORIGINAL_CASES  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
QWEN_MODEL = "qwen2.5:7b-instruct"
HAIKU_MODEL = "claude-haiku-4-5"

FREQ_ENUM = [
    "ONCE_DAILY", "BID", "TID", "QID", "BEDTIME", "WITH_MEALS",
    "PRN", "WEEKLY", "EVERY_N_HOURS", "TAPER", "UNKNOWN",
]

# ---------------------------------------------------------------------------
# HELD-OUT ground truth. `times` is the list the app should store as reminder
# times (sorted); None = don't score times for this med. `freq_ok` lists every
# acceptable frequency label (first = canonical).
# ---------------------------------------------------------------------------
HELDOUT_CASES = [
    {
        "id": "H1-vial-classic-once-daily",
        "text": """Shoppers Drug Mart #1123
555 King St W, Kitchener ON N2G 1B5  (519) 555-8100
Rx: 1234567  Dr. G. Singh
MUTHURAJ JAYAKUMAR
APO-AMLODIPINE 5 MG TABLET
TAKE 1 TABLET BY MOUTH ONCE DAILY
Qty: 90  Refills: 3  DIN: 02273373
""",
        "meds": [{"name": "amlodipine", "dosage": "5mg",
                  "freq_ok": ["ONCE_DAILY"], "times": ["08:00"], "prn": False}],
    },
    {
        "id": "H2-DANGER-weekly-alendronate",
        "text": """Rexall Pharmacy
APO-ALENDRONATE 70 MG TABLET
TAKE 1 TABLET ONCE WEEKLY ON AN EMPTY STOMACH WITH A FULL GLASS OF WATER
REMAIN UPRIGHT FOR 30 MINUTES AFTER TAKING
Qty: 4  Refills: 2
""",
        "meds": [{"name": "alendronate", "dosage": "70mg",
                  "freq_ok": ["WEEKLY"], "times": [], "prn": False}],
        "danger": "weekly",
    },
    {
        "id": "H3-every-8-hours",
        "text": """WATERLOO FAMILY PHARMACY
AMOXICILLIN 500 MG CAPSULES
Take 1 capsule every 8 hours until all finished
Qty: 21  Refills: 0
""",
        "meds": [{"name": "amoxicillin", "dosage": "500mg",
                  "freq_ok": ["EVERY_N_HOURS", "TID"], "times": None, "prn": False}],
    },
    {
        "id": "H4-bare-daily",
        "text": """Costco Pharmacy
RAMIPRIL 10 MG CAPSULE
Take 1 capsule daily
Qty: 30  Refills: 5
""",
        "meds": [{"name": "ramipril", "dosage": "10mg",
                  "freq_ok": ["ONCE_DAILY"], "times": ["08:00"], "prn": False}],
    },
    {
        "id": "H5-prednisone-taper",
        "text": """Guardian Drugs
PREDNISONE 5 MG TABLET
Take 4 tablets daily for 3 days, then 3 tablets daily for 3 days,
then 2 tablets daily for 3 days, then 1 tablet daily for 3 days, then stop
Qty: 30  Refills: 0
""",
        "meds": [{"name": "prednisone", "dosage": "5mg",
                  "freq_ok": ["TAPER", "ONCE_DAILY", "UNKNOWN"], "times": None, "prn": False}],
    },
    {
        "id": "H6-split-dose-morning-bedtime",
        "text": """Pharmasave
APO-METFORMIN 500 MG TABLET
Take 1 tablet in the morning and 2 tablets at bedtime with food
Qty: 90  Refills: 2
""",
        "meds": [{"name": "metformin", "dosage": "500mg",
                  "freq_ok": ["BID", "BEDTIME", "UNKNOWN"],
                  "times": ["08:00", "21:00"], "prn": False}],
    },
    {
        "id": "H7-french-quebec-bid",
        "text": """Jean Coutu Pharmacie
1200 rue Sainte-Catherine, Montreal QC
LOSARTAN 50 MG COMPRIME
PRENDRE 1 COMPRIME 2 FOIS PAR JOUR AVEC DE LA NOURRITURE
Qte: 60  Renouvellements: 3
""",
        "meds": [{"name": "losartan", "dosage": "50mg",
                  "freq_ok": ["BID", "WITH_MEALS"], "times": ["08:00", "18:00"],
                  "prn": False}],
    },
    {
        "id": "H8-sig-codes-synthroid",
        "text": """Medicine Shoppe Pharmacy
SYNTHROID 88 MCG TABLET
1 TAB PO QD AM 30 MIN BEFORE BREAKFAST
Qty: 90  Refills: 11  DIN: 02172078
""",
        "meds": [{"name": "synthroid", "dosage": "88mcg",
                  "freq_ok": ["ONCE_DAILY"], "times": ["08:00"], "prn": False}],
    },
    {
        "id": "H9-unenumerated-no-strength-2med",
        "text": """London Drugs
Rosuvastatin - take one tablet at bedtime
Vitamin D - take one tablet daily
Pharmacist: T. Nguyen
""",
        "meds": [{"name": "rosuvastatin", "dosage": None,
                  "freq_ok": ["BEDTIME"], "times": ["21:00"], "prn": False},
                 {"name": "vitamin d", "dosage": None,
                  "freq_ok": ["ONCE_DAILY"], "times": ["08:00"], "prn": False}],
    },
    {
        "id": "H10-ocr-noise-atorvastatin",
        "text": """C0STCO PHARMACY
AT0RVASTATIN 2O MG TABLET
TAKE 1 TABLET AT BEDTlME
0ty: 9O Refi11s: 2
""",
        "meds": [{"name": "atorvastatin", "dosage": "20mg",
                  "freq_ok": ["BEDTIME"], "times": ["21:00"], "prn": False}],
        "ocr_noise": True,
    },
    {
        "id": "H11-half-tablet-digoxin",
        "text": """Pharmaprix
TEVA-DIGOXIN 0.125 MG TABLET
TAKE ONE HALF TABLET ONCE DAILY
MAY CAUSE DIZZINESS - AVOID SUDDEN STANDING
Qty: 45  Refills: 2
""",
        "meds": [{"name": "digoxin", "dosage": "0.125mg",
                  "freq_ok": ["ONCE_DAILY"], "times": ["08:00"], "prn": False}],
    },
    {
        "id": "H12-insulin-units-non-oral-solid",
        "text": """Shoppers Drug Mart
LANTUS SOLOSTAR 100 UNITS/ML PEN
INJECT 20 UNITS SUBCUTANEOUSLY AT BEDTIME
Qty: 5 pens  Refills: 2
""",
        "meds": [{"name": "lantus", "dosage": None,  # dosage-per-use is 20 units; strength 100 units/mL -- accept either or None
                  "freq_ok": ["BEDTIME", "ONCE_DAILY"], "times": ["21:00"], "prn": False}],
        "units_ok": ["20units", "100units/ml", "20 units", "100 units/ml"],
    },
]

# ---------------------------------------------------------------------------
# ORIGINAL-12 per-field ground truth (the "widening").
#
# Historically the original 12 were scored on medication COUNT + name
# fragments only -- blind to frequency, dosage and reminder-time errors. That
# blindness is why the published "0 safety events" was only ever a statement
# about the HELD-OUT 12: qwen2.5:7b turning C's "at bedtime as needed" into a
# fixed 21:00 reminder (unflagged) could not register on this arm.
#
# Authored by reading ONLY each label's own text in redteam_probe_splitter.py.
# NO model output (qwen, Haiku, regex) was consulted -- deriving eval truth
# from a model's own output is the NB04 self-distillation trap in eval form,
# and would blind the harness to exactly the error class this exists to catch.
# Reviewed + approved by Muthu 2026-07-29 with ZERO field corrections; the
# case-by-case walkthrough (incl. the three judgement calls: brand-vs-generic
# naming, BID+WITH_MEALS admission, J's explicit clock times) is the dev-
# workspace record `Brainstorm/.claude/muthuverificationperfieldtruth.md`
# alongside `original_12_perfield_DRAFT.json` (not shipped -- see Journey.md).
#
# Same shape as HELDOUT_CASES[*]["meds"], and scored by the same
# `score_heldout` function, so the two arms are measured identically.
# ---------------------------------------------------------------------------
ORIGINAL_PERFIELD = {
    "A-numbered-sig-5med (the real synthetic doc's shape)": [
        {"name": 'tylenol', "dosage": '500mg',
         "freq_ok": ['PRN', 'EVERY_N_HOURS'], "times": [], "prn": True},
        {"name": 'advil', "dosage": '200mg',
         "freq_ok": ['EVERY_N_HOURS'], "times": [], "prn": False},
        {"name": 'benadryl', "dosage": '25mg',
         "freq_ok": ['BEDTIME'], "times": ['21:00'], "prn": False},
        {"name": 'pepcid', "dosage": '20mg',
         "freq_ok": ['ONCE_DAILY'], "times": ['08:00'], "prn": False},
        {"name": 'allergy', "dosage": '10mg',
         "freq_ok": ['ONCE_DAILY'], "times": ['08:00'], "prn": False},
    ],
    'B-numbered-no-sig-3med': [
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID', 'WITH_MEALS'], "times": ['08:00', '18:00'], "prn": False},
        {"name": 'ramipril', "dosage": '5mg',
         "freq_ok": ['ONCE_DAILY'], "times": ['08:00'], "prn": False},
        {"name": 'atorvastatin', "dosage": '20mg',
         "freq_ok": ['BEDTIME'], "times": ['21:00'], "prn": False},
    ],
    'C-unenumerated-stacked-2med (dosage fallback must catch)': [
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID', 'WITH_MEALS'], "times": ['08:00', '18:00'], "prn": False},
        # The anchor case. `freq_ok` is PRN ONLY -- deliberately excluding
        # BEDTIME -- because this truth exists to catch the observed qwen bug
        # ("at bedtime as needed" -> BEDTIME + a fabricated 21:00, no flag).
        # Adding BEDTIME here silently defeats the reason this arm was widened.
        {"name": 'naproxen', "dosage": '500mg',
         "freq_ok": ['PRN'], "times": [], "prn": True},
    ],
    'D-PHANTOM-TRAP single med + mg max-dose line': [
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID', 'WITH_MEALS'], "times": ['08:00', '18:00'], "prn": False},
    ],
    'E-PHANTOM-TRAP single med + generic-name restatement': [
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID', 'WITH_MEALS'], "times": ['08:00', '18:00'], "prn": False},
    ],
    'F-PHANTOM-TRAP single med + total-daily note': [
        {"name": 'ramipril', "dosage": '5mg',
         "freq_ok": ['ONCE_DAILY'], "times": ['08:00'], "prn": False},
    ],
    'G-PHANTOM-TRAP numbered counselling notes, single med': [
        {"name": 'amoxicillin', "dosage": '500mg',
         "freq_ok": ['TID', 'WITH_MEALS'], "times": ['08:00', '13:00', '18:00'], "prn": False},
    ],
    'H-PHANTOM-TRAP garbled 1000+ char dump, single med': [
        {"name": 'amoxicillin', "dosage": '500mg',
         "freq_ok": ['TID', 'WITH_MEALS'], "times": ['08:00', '13:00', '18:00'], "prn": False},
    ],
    'I-single-numbered-item (1 anchor only, must not split)': [
        {"name": 'telmisartan', "dosage": '40mg',
         "freq_ok": ['ONCE_DAILY'], "times": ['08:00'], "prn": False},
    ],
    'J-clock-times-2med': [
        # times are [08:00, 20:00], NOT BID's canonical [08:00, 18:00]: the
        # label literally prints "8:00 AM and 8:00 PM". Defaulting here would
        # mean ignoring an explicit instruction printed on the label.
        {"name": 'atorvastatin', "dosage": '20mg',
         "freq_ok": ['BID'], "times": ['08:00', '20:00'], "prn": False},
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID'], "times": ['08:00', '18:00'], "prn": False},
    ],
    'K-single-med-classic (must stay 1, unchanged)': [
        {"name": 'acetaminophen', "dosage": '500mg',
         "freq_ok": ['PRN', 'EVERY_N_HOURS'], "times": [], "prn": True},
    ],
    'L-demo-text (OCR_PIPELINE_ENABLED=false path, must stay 1)': [
        {"name": 'metformin', "dosage": '500mg',
         "freq_ok": ['BID', 'WITH_MEALS'], "times": ['08:00', '18:00'], "prn": False},
    ],
}


def _build_original_perfield_cases():
    """Join ORIGINAL_CASES with ORIGINAL_PERFIELD into score_heldout's shape.

    The two invariants are enforced at import time on purpose: a truth that
    silently drifts out of alignment with the label it scores is worse than a
    crash, because it produces confident wrong numbers.
    """
    out = []
    for case_id, expected, _fragments, text in ORIGINAL_CASES:
        if case_id not in ORIGINAL_PERFIELD:
            raise AssertionError(f"no per-field truth for original case {case_id!r}")
        meds = ORIGINAL_PERFIELD[case_id]
        if len(meds) != expected:
            raise AssertionError(
                f"{case_id!r}: per-field truth has {len(meds)} meds but "
                f"expected_medication_count is {expected}")
        out.append({"id": case_id, "text": text, "meds": meds})
    extra = set(ORIGINAL_PERFIELD) - {c[0] for c in ORIGINAL_CASES}
    if extra:
        raise AssertionError(f"per-field truths for unknown cases: {sorted(extra)}")
    return out


ORIGINAL_PERFIELD_CASES = _build_original_perfield_cases()

PROMPT = """You extract structured medication data from the raw OCR text of a Canadian pharmacy prescription label.

Return ONLY a JSON object: {"medications": [...]} -- one entry per DISTINCT medication actually present on the label.

Each entry has exactly these fields:
- "drug_name": string, the medication name including strength as printed (e.g. "APO-METFORMIN 500 MG")
- "dosage": string strength as printed (e.g. "500 mg") or null if no strength is printed
- "frequency_type": one of ONCE_DAILY, BID, TID, QID, BEDTIME, WITH_MEALS, PRN, WEEKLY, EVERY_N_HOURS, TAPER, UNKNOWN
- "specific_times": array of 24h "HH:MM" reminder times, derived as specified below
- "with_food": boolean

Deriving specific_times (these are the app's reminder defaults -- follow them exactly):
- explicit clock times on the label override everything (e.g. "8:00 PM" -> "20:00")
- morning=08:00, afternoon=13:00, evening=18:00, night or bedtime=21:00
- ONCE_DAILY -> ["08:00"]; BID -> ["08:00","18:00"]; TID -> ["08:00","13:00","18:00"]; QID -> ["08:00","13:00","18:00","21:00"]
- PRN (as-needed) -> [] always. WEEKLY -> [] (no fixed daily time). EVERY_N_HOURS, TAPER, UNKNOWN -> []

Hard rules:
- NEVER invent a medication, strength, or time that is not on the label.
- Pharmacy names, addresses, phone numbers, doctors, patient names, quantities, refills, DINs, and warning/counselling lines are NOT medications.
- If unsure of any field, use null / UNKNOWN / [] rather than guessing.
- The label may be in French; extract the same fields.

LABEL TEXT:
"""


def _norm_dose(s):
    if not s:
        return None
    return re.sub(r"\s+", "", str(s)).lower().replace(",", ".")


def _norm_text(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


REGEX_FREQ_MAP = {
    "ONCE_DAILY": "ONCE_DAILY", "BID": "BID", "TID": "TID", "QID": "QID",
    "BEDTIME": "BEDTIME", "WITH_MEALS": "WITH_MEALS", "PRN": "PRN",
    "UNKNOWN": "UNKNOWN",
}


def run_regex(text):
    t0 = time.perf_counter()
    meds = parse_medications(text)
    dt = time.perf_counter() - t0
    out = []
    for m in meds:
        out.append({
            "drug_name": m.drug_name,
            "dosage": m.dosage,
            "frequency_type": REGEX_FREQ_MAP.get(m.frequency_type, m.frequency_type),
            "specific_times": list(m.specific_times),
            "with_food": bool(m.with_food),
        })
    return out, dt, None


def _extract_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in output: {raw[:200]!r}")
    return json.loads(raw[start:end + 1])


def run_qwen(text):
    body = json.dumps({
        "model": QWEN_MODEL,
        "messages": [{"role": "user", "content": PROMPT + text}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 8192},
        "keep_alive": "10m",
    }).encode()
    t0 = time.perf_counter()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    dt = time.perf_counter() - t0
    data = _extract_json(resp["message"]["content"])
    return data.get("medications", []), dt, None


# ---------------------------------------------------------------------------
# FixbyOPUS3 §7 -- the shipped path, end to end.
# ---------------------------------------------------------------------------

#: Filled by run_via_service so the summary can report which proposer actually
#: spoke per case, and prove the WEEKLY/PRN no-times invariant.
VIA_SERVICE_AUDIT: list[dict] = []


def run_via_service(text):
    """Route one label through the real sidecar + guardrails + derivation.

    Deliberately calls `routes.prescriptions._propose_medications` -- the
    route's own helper -- rather than re-implementing the sequence here. A
    harness that re-implements the thing it is measuring measures the
    re-implementation.
    """
    import asyncio

    from app.api.v1.routes import prescriptions as rx_route

    t0 = time.perf_counter()
    proposals, parse_source = asyncio.run(rx_route._propose_medications(text))
    dt = time.perf_counter() - t0

    out = []
    for med in proposals:
        out.append({
            "drug_name": med.drug_name,
            "dosage": med.dosage,
            "frequency_type": med.frequency_type,
            # The scored field is the DERIVED reminder-time list -- what the
            # app would actually persist and remind on.
            "specific_times": list(med.specific_times),
            "explicit_times": list(med.explicit_times),
            "with_food": bool(med.with_food),
            "flags": list(med.flags),
            "parse_source": parse_source,
        })
    VIA_SERVICE_AUDIT.append({"parse_source": parse_source, "medications": out})
    return out, dt, None


_HAIKU_CLIENT = None


def _load_api_key():
    for envp in (REPO / ".env", REPO / "dev" / "backend" / ".env"):
        if envp.exists():
            for line in envp.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("LLM_API_KEY=") and len(line.strip()) > 20:
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("no LLM_API_KEY found in .env files")


def run_haiku(text):
    global _HAIKU_CLIENT
    import anthropic
    if _HAIKU_CLIENT is None:
        _HAIKU_CLIENT = anthropic.Anthropic(api_key=_load_api_key())
    t0 = time.perf_counter()
    resp = _HAIKU_CLIENT.messages.create(
        model=HAIKU_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": PROMPT + text}],
    )
    dt = time.perf_counter() - t0
    raw = "".join(b.text for b in resp.content if b.type == "text")
    data = _extract_json(raw)
    usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return data.get("medications", []), dt, usage


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_original(case, meds):
    """ORIGINAL set: count + name-fragment scoring only (matches probe_splitter)."""
    case_id, expected, fragments, text = case
    got = len(meds)
    names = " | ".join(str(m.get("drug_name", "")) for m in meds).lower()
    missing = [f for f in (fragments or []) if f not in names]
    return {
        "case": case_id, "expected": expected, "got": got,
        "missed": got < expected, "phantom": got > expected,
        "names_missing": missing,
        "ok": got == expected and not missing,
    }


def score_heldout(case, meds):
    truth = case["meds"]
    got = len(meds)
    expected = len(truth)
    events = []
    if got > expected:
        events.append("PHANTOM_MED")
    if got < expected:
        events.append("MISSED_MED")

    text_norm = _norm_text(case["text"])
    per_med = []
    used = set()
    for t in truth:
        # align: first emitted med whose name contains the fragment, else positional
        match = None
        for i, m in enumerate(meds):
            if i in used:
                continue
            if t["name"].replace(" ", "") in _norm_text(str(m.get("drug_name", ""))):
                match = (i, m)
                break
        if match is None and meds:
            for i, m in enumerate(meds):
                if i not in used:
                    match = (i, m)
                    break
        if match is None:
            per_med.append({"truth": t["name"], "found": False})
            continue
        i, m = match
        used.add(i)
        name_ok = t["name"].replace(" ", "") in _norm_text(str(m.get("drug_name", "")))
        emitted_dose = _norm_dose(m.get("dosage"))
        if t["dosage"] is None:
            ok_doses = [None] + [_norm_dose(u) for u in case.get("units_ok", [])]
            dose_ok = emitted_dose in ok_doses
        else:
            dose_ok = emitted_dose == t["dosage"]
        freq = str(m.get("frequency_type", "UNKNOWN")).upper()
        freq_ok = freq in t["freq_ok"]
        times = sorted(str(x) for x in (m.get("specific_times") or []))
        times_ok = None if t["times"] is None else (times == sorted(t["times"]))

        # safety events
        if t["prn"] and times:
            events.append("TIMES_FOR_PRN")
        if case.get("danger") == "weekly" and times:
            events.append("DAILY_TIMES_FOR_WEEKLY")
        if emitted_dose and not case.get("ocr_noise"):
            if _norm_text(emitted_dose) not in text_norm:
                events.append(f"DOSAGE_NOT_ON_LABEL:{emitted_dose}")
        if not name_ok and m.get("drug_name") and not case.get("ocr_noise"):
            if _norm_text(str(m["drug_name"]))[:8] not in text_norm:
                events.append(f"NAME_NOT_ON_LABEL:{m['drug_name']}")

        per_med.append({
            "truth": t["name"], "found": True, "name_ok": name_ok,
            "dose_ok": dose_ok, "freq": freq, "freq_ok": freq_ok,
            "times": times, "times_ok": times_ok,
            "emitted_name": m.get("drug_name"), "emitted_dose": m.get("dosage"),
        })

    fields_scored = fields_ok = 0
    for pm in per_med:
        if not pm["found"]:
            fields_scored += 4
            continue
        for k in ("name_ok", "dose_ok", "freq_ok", "times_ok"):
            if pm.get(k) is not None:
                fields_scored += 1
                fields_ok += 1 if pm[k] else 0
    return {
        "case": case["id"], "expected": expected, "got": got,
        "events": events, "per_med": per_med,
        "fields_ok": fields_ok, "fields_scored": fields_scored,
        "fully_ok": (got == expected and not events
                     and all(pm.get(k) in (True, None)
                             for pm in per_med
                             for k in ("name_ok", "dose_ok", "freq_ok", "times_ok"))),
    }


def summarize(orig, orig_pf, held):
    """One arm's numbers for one run.

    `orig_ok` is retained unchanged so the widened runs stay directly
    comparable to the pre-widening published record; everything else is new.

    **Safety events and errors are counted separately, and deliberately so**
    (2026-07-29). A safety event is a defect in what the system EXTRACTED --
    a daily reminder on a once-weekly bisphosphonate, times attached to a PRN
    medication, a dropped medication. An error is the call failing outright
    (an empty Ollama response, a timeout): the extraction never happened, so
    there is nothing to be wrong about. Both are real production risks and
    both stay counted -- but folding an infrastructure failure into the
    safety-event column reports a parsing defect that did not occur, which is
    the same dishonesty as re-baselining, just pointing the other way. An
    errored case still scores 0 fields and `fully_ok=False`; it is never
    silently excused.
    """
    def _fields(rows):
        return (sum(r.get("fields_ok", 0) for r in rows),
                sum(r.get("fields_scored", 0) for r in rows))

    def _events(rows):
        return sum(len(r.get("events", [])) for r in rows)

    def _errors(rows):
        return sum(1 for r in rows if r.get("errored"))

    o_ok, o_sc = _fields(orig_pf)
    h_ok, h_sc = _fields(held)
    return {
        "orig_ok": sum(1 for s in orig if s.get("ok")),
        "orig_phantom": sum(1 for s in orig if s.get("phantom")),
        "orig_fully_ok": sum(1 for s in orig_pf if s.get("fully_ok")),
        "orig_fields": f"{o_ok}/{o_sc}",
        "orig_events": _events(orig_pf),
        "orig_errors": _errors(orig_pf),
        "held_fully_ok": sum(1 for s in held if s.get("fully_ok")),
        "held_fields": f"{h_ok}/{h_sc}",
        "held_events": _events(held),
        "held_errors": _errors(held),
        "all_fields": f"{o_ok + h_ok}/{o_sc + h_sc}",
        "all_events": _events(orig_pf) + _events(held),
        "all_errors": _errors(orig_pf) + _errors(held),
        "_sort_fields_ok": o_ok + h_ok,
    }


def _signature(score):
    """Run-to-run fingerprint of one arm's answer on one label.

    Compares what the system actually EMITTED (name/dosage/frequency/times),
    not merely whether it scored well -- two runs can both be wrong in
    different ways, and that is exactly the nondeterminism worth measuring.
    """
    return json.dumps({
        "got": score.get("got"),
        "events": sorted(score.get("events", [])),
        # A failed call IS a different outcome, so it belongs in the
        # fingerprint -- but it is reported flagged (see the nondeterminism
        # block), because "the model answered differently" and "the model
        # did not answer" are different claims and only the first one is
        # evidence about the model.
        "errored": bool(score.get("errored")),
        "per_med": [
            {k: pm.get(k) for k in
             ("truth", "found", "emitted_name", "emitted_dose", "freq", "times")}
            for pm in score.get("per_med", [])
        ],
    }, sort_keys=True, default=str)


def evaluate_arm(name, fn, usage_sink):
    """One full pass of one system over all 24 labels."""
    if name == "via-service":
        VIA_SERVICE_AUDIT.clear()
    orig, orig_pf, held, lats = [], [], [], []

    for case, pf_case in zip(ORIGINAL_CASES, ORIGINAL_PERFIELD_CASES):
        assert case[0] == pf_case["id"], "original case / per-field truth misalignment"
        try:
            meds, dt, usage = fn(case[3])
        except Exception as e:  # noqa: BLE001
            print(f"  [O] {case[0][:44]:<46} ERROR {e}")
            orig.append({"case": case[0], "error": str(e), "ok": False,
                         "missed": True, "phantom": False, "names_missing": []})
            orig_pf.append({"case": case[0], "error": str(e), "fully_ok": False,
                            "events": [], "errored": True, "fields_ok": 0,
                            "fields_scored": len(pf_case["meds"]) * 4,
                            "expected": len(pf_case["meds"]), "got": 0, "per_med": []})
            continue
        s = score_original(case, meds)
        pf = score_heldout(pf_case, meds)
        lats.append(dt)
        if usage:
            usage_sink.append(usage)
        flag = "ok" if s["ok"] else ("PHANTOM" if s["phantom"] else
                                     ("MISSED" if s["missed"] else f"NAME{s['names_missing']}"))
        ev = ",".join(pf["events"]) if pf["events"] else "-"
        print(f"  [O] {case[0][:44]:<46} exp={s['expected']} got={s['got']} {flag} "
              f"fields {pf['fields_ok']}/{pf['fields_scored']} events={ev} ({dt:.1f}s)")
        orig.append(s)
        orig_pf.append(pf)

    for case in HELDOUT_CASES:
        try:
            meds, dt, usage = fn(case["text"])
        except Exception as e:  # noqa: BLE001
            print(f"  [H] {case['id']:<46} ERROR {e}")
            held.append({"case": case["id"], "error": str(e), "fully_ok": False,
                         "events": [], "errored": True, "fields_ok": 0,
                         "fields_scored": 4,
                         "expected": len(case["meds"]), "got": 0, "per_med": []})
            continue
        s = score_heldout(case, meds)
        lats.append(dt)
        if usage:
            usage_sink.append(usage)
        ev = ",".join(s["events"]) if s["events"] else "-"
        print(f"  [H] {case['id']:<46} exp={s['expected']} got={s['got']} "
              f"fields {s['fields_ok']}/{s['fields_scored']} events={ev} ({dt:.1f}s)")
        held.append(s)

    latency = {"mean_s": round(sum(lats) / max(len(lats), 1), 2),
               "max_s": round(max(lats), 2) if lats else 0}
    return orig, orig_pf, held, latency


def export_labels(path):
    """The published `labels_and_ground_truth.json` -- both case sets and
    their truths, so the evaluation set is inspectable without reading this
    file (FixbyOPUS3 §8)."""
    payload = {
        "note": (
            "PillSafe Rx-extraction evaluation set. ORIGINAL 12 are the regex "
            "parser's own development fixtures (its home turf); HELD-OUT 12 were "
            "authored fresh by the SA and never used to tune any parser. "
            "`times` is the reminder-time list the app should STORE (derived), "
            "and null means times are not scored for that medication. "
            "Both sets now carry per-field truths and are scored by the same "
            "function; `per_field_meds` on the original 12 was added 2026-07-29 "
            "(20 medications x 4 fields = 80 newly scored fields, 50 -> 130 "
            "overall), authored from each label's own text and reviewed with "
            "zero corrections. Before that date the original 12 were scored on "
            "medication count + name fragments only, so frequency/dosage/time "
            "errors on those labels -- including a PRN medication given a fixed "
            "daily reminder -- were invisible."
        ),
        "original_12": [
            {"id": c[0], "expected_medication_count": c[1],
             "name_fragments": list(c[2] or []),
             "per_field_meds": ORIGINAL_PERFIELD[c[0]], "text": c[3]}
            for c in ORIGINAL_CASES
        ],
        "heldout_12": HELDOUT_CASES,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"labels + ground truth -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-qwen", action="store_true")
    ap.add_argument("--skip-haiku", action="store_true")
    ap.add_argument(
        "--via-service", action="store_true",
        help="FixbyOPUS3 §7 acceptance mode: route the labels through the real "
             "sidecar + guardrails + deterministic derivation (see module docstring).",
    )
    ap.add_argument(
        "--repeats", type=int, default=1, metavar="N",
        help="Run every arm N times. qwen2.5:7b at temperature 0 is MEASURED "
             "non-deterministic, so a single run cannot honestly claim an "
             "intermittent error class is absent; N>1 reports per-run numbers, "
             "the worst run, and which labels differed across runs.",
    )
    ap.add_argument(
        "--export-labels", metavar="PATH", default=None,
        help="Dump the 24 labels + ground truths to PATH as JSON and exit.",
    )
    args = ap.parse_args()

    if args.export_labels:
        export_labels(Path(args.export_labels))
        return 0

    if args.via_service:
        systems = {"via-service": run_via_service}
    else:
        systems = {"regex": run_regex}
        if not args.skip_qwen:
            systems["qwen2.5:7b"] = run_qwen
        if not args.skip_haiku:
            systems["haiku-4.5"] = run_haiku

    repeats = max(1, args.repeats)
    results = {
        "protocol": {
            "repeats": repeats,
            "scoring": "per-field on BOTH arms (original 12 widened 2026-07-29)",
            "original_fields": sum(3 + (1 if m["times"] is not None else 0)
                                   for c in ORIGINAL_PERFIELD_CASES for m in c["meds"]),
            "heldout_fields": sum(3 + (1 if m["times"] is not None else 0)
                                  for c in HELDOUT_CASES for m in c["meds"]),
            "arms": list(systems),
        },
        "runs": [], "haiku_usage": [],
    }
    via_service_runs = []

    # Run-major: every arm answers run 1 before any arm answers run 2, so a
    # later run is never advantaged by a warmer cache than an earlier one.
    for r in range(1, repeats + 1):
        run = {"run": r, "original": {}, "original_perfield": {},
               "heldout": {}, "latency": {}}
        for name, fn in systems.items():
            print(f"\n=== {name}  (run {r}/{repeats}) ===")
            orig, orig_pf, held, latency = evaluate_arm(name, fn, results["haiku_usage"])
            run["original"][name] = orig
            run["original_perfield"][name] = orig_pf
            run["heldout"][name] = held
            run["latency"][name] = latency
            if name == "via-service":
                via_service_runs.append(list(VIA_SERVICE_AUDIT))
        results["runs"].append(run)

    # ---- summary ----
    summary_per_run = {name: [] for name in systems}
    for run in results["runs"]:
        for name in systems:
            s = summarize(run["original"][name], run["original_perfield"][name],
                          run["heldout"][name])
            s["run"] = run["run"]
            s["mean_lat_s"] = run["latency"][name]["mean_s"]
            summary_per_run[name].append(s)

    # The reported headline is the WORST run, not the mean: for an
    # intermittent safety error, "it usually does not happen" is not a claim
    # a medication app gets to make. Safety events dominate the ordering,
    # then call errors, then field accuracy -- an extraction defect is worse
    # than a failed call, and a failed call is worse than a lost field.
    summary_worst = {
        name: max(rows, key=lambda s: (s["all_events"], s["all_errors"],
                                       -s["_sort_fields_ok"]))
        for name, rows in summary_per_run.items()
    }

    print("\n" + "=" * 130)
    print(f"PER-FIELD SCORING, {repeats} run(s) per arm -- worst run reported "
          f"(published pre-widening numbers scored only the held-out 12)")
    print("'ev' = safety events (extraction defects). 'err' = failed calls "
          "(no extraction happened). Counted separately -- see summarize().")
    print(f"{'system':<14} {'orig ok':>8} {'orig full':>10} {'orig fields':>12} "
          f"{'orig ev':>8} {'held full':>10} {'held fields':>12} {'held ev':>8} "
          f"{'ALL fields':>12} {'ALL ev':>7} {'ALL err':>8} {'mean lat':>9}")
    print("-" * 130)
    for name, s in summary_worst.items():
        print(f"{name:<14} {s['orig_ok']:>5}/12 {s['orig_fully_ok']:>7}/12 "
              f"{s['orig_fields']:>12} {s['orig_events']:>8} "
              f"{s['held_fully_ok']:>7}/12 {s['held_fields']:>12} {s['held_events']:>8} "
              f"{s['all_fields']:>12} {s['all_events']:>7} {s['all_errors']:>8} "
              f"{s['mean_lat_s']:>8}s")

    # ---- nondeterminism ----
    nondet = {}
    if repeats > 1:
        print("\n" + "-" * 118)
        print(f"RUN-TO-RUN STABILITY over {repeats} runs (emitted "
              f"name/dosage/frequency/times compared, all 24 labels)")
        for name in systems:
            differing = []
            for key in ("original_perfield", "heldout"):
                n_cases = len(results["runs"][0][key][name])
                for i in range(n_cases):
                    sigs = {_signature(run[key][name][i]) for run in results["runs"]}
                    if len(sigs) > 1:
                        involved_error = any(run[key][name][i].get("errored")
                                             for run in results["runs"])
                        differing.append({
                            "case": results["runs"][0][key][name][i].get("case"),
                            "arm_set": "original" if key == "original_perfield" else "heldout",
                            "distinct_answers": len(sigs),
                            "involved_error": involved_error,
                        })
            # Split the count: only the error-free differences are evidence
            # about the MODEL's run-to-run stability. A label that differed
            # solely because one call failed says nothing about temperature-0
            # determinism, and reporting it as if it did would overstate the
            # nondeterminism finding.
            model_diff = [d for d in differing if not d["involved_error"]]
            err_diff = [d for d in differing if d["involved_error"]]
            nondet[name] = {"n_labels_differing": len(differing),
                            "n_labels_differing_model_only": len(model_diff),
                            "n_labels_differing_error_involved": len(err_diff),
                            "labels": differing}
            ids = ", ".join(d["case"][:34] + ("*" if d["involved_error"] else "")
                            for d in differing) or "-"
            print(f"  {name:<14} {len(model_diff):>2}/24 labels differed "
                  f"(+{len(err_diff)} error-involved, marked *)   {ids}")
    results["nondeterminism"] = nondet

    results["summary_per_run"] = summary_per_run
    results["summary_worst"] = summary_worst
    if results["haiku_usage"]:
        tin = sum(u["in"] for u in results["haiku_usage"])
        tout = sum(u["out"] for u in results["haiku_usage"])
        cost = tin / 1e6 * 1.00 + tout / 1e6 * 5.00
        results["haiku_cost_usd"] = round(cost, 4)
        print(f"\nhaiku tokens: {tin} in / {tout} out over {repeats} run(s) ~= ${cost:.4f}")

    if args.via_service:
        # The rest of the pre-registered §7 bar, checked here rather than by
        # eye. TWO checks, and the gap between them IS the finding of
        # 2026-07-30 -- keep both, and read only the second as evidence.
        #
        # SELF-REPORTED (the original §7 invariant): no medication whose
        # emitted `frequency_type` is WEEKLY/PRN may carry a reminder time.
        # It is STRUCTURALLY BLIND to the label-C defect and always was. The
        # shipped path emitted BEDTIME + ['21:00'] for "at bedtime as needed
        # for pain", so this check found zero offenders -- correctly, by its
        # own terms, because the misclassification is the defect. An
        # invariant over a system's own classification goes quiet exactly
        # when the classification is what failed. Retained to document that.
        #
        # TRUTH-SIDE (the bar that counts): every medication the HUMAN-
        # APPROVED ground truth marks `prn: true` must carry no times,
        # whatever the pipeline called it. This is the `TIMES_FOR_PRN` event
        # the per-field scorer already raises; surfacing it here is what
        # makes the §7 bar able to fail.
        self_reported = [
            dict(m, run=i + 1) for i, audit in enumerate(via_service_runs)
            for entry in audit for m in entry["medications"]
            if m["frequency_type"] in ("WEEKLY", "PRN") and m["specific_times"]
        ]
        truth_side = [
            {"run": run["run"], "case": scored["case"],
             "events": [e for e in scored["events"] if e == "TIMES_FOR_PRN"],
             "per_med": [pm for pm in scored["per_med"] if pm.get("times")]}
            for run in results["runs"]
            for arm in ("original_perfield", "heldout")
            for scored in run[arm].get("via-service", [])
            if "TIMES_FOR_PRN" in scored.get("events", [])
        ]
        sources = sorted({entry["parse_source"] for audit in via_service_runs
                          for entry in audit})
        results["via_service_audit"] = {
            "parse_sources_seen": sources,
            "weekly_or_prn_with_times": self_reported,
            "self_reported_note": (
                "Reads the pipeline's OWN frequency_type. Blind by "
                "construction when the classification is the defect "
                "(label C, 2026-07-30). Not evidence on its own."
            ),
            "prn_by_ground_truth_with_times": truth_side,
            "per_run": via_service_runs,
        }
        print(f"\nvia-service parse sources: {sources}")
        print(f"via-service [self-reported] WEEKLY/PRN medications carrying "
              f"times: {len(self_reported)} "
              f"{'(vacuous unless the truth-side check agrees)' if not self_reported else '(FAIL) ' + repr(self_reported)}")
        print(f"via-service [TRUTH-SIDE] ground-truth-PRN medications carrying "
              f"times, across all {repeats} run(s): {len(truth_side)} "
              f"{'(PASS)' if not truth_side else '(FAIL) ' + repr(truth_side)}")

        out = HERE / "redteam_llm_extraction_perfield_via_service_results.json"
    else:
        out = HERE / "redteam_llm_extraction_perfield_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
