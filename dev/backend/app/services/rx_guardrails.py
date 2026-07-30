"""Deterministic guardrails over Rx medication PROPOSALS (FixbyOPUS3 Task A2).

Applied to every proposal list regardless of which proposer produced it --
the local qwen2.5:7b sidecar (`/rx/extract`) or the regex fallback
(`prescription_parser.parse_medications`). That symmetry is the point: the
proposer is swappable behind one config value, the safety layer is not.

Guard set transplanted from MEDIC (Nature Medicine, 2024 -- catalog
cross-check + halt conditions + abstain-over-generate):

  G1 catalog          -- name not found in the DIN reference => flag
  G2 no-invention     -- values not supported by the label => strip (times)
                         or KEEP-AND-FLAG (name/dosage), never silently
                         rewritten
  G3 schema           -- frequency outside the enum => UNKNOWN; malformed
                         clock times dropped
  G4 no-silent-default-- reminder times DERIVED here, server-side, from
     + derivation        frequency_type; PRN/WEEKLY/EVERY_N_HOURS/TAPER/
                         UNKNOWN get [] plus `needs_schedule`
  G5 conflict         -- duplicate names / conflicting dosages => flag
  G6 as-needed        -- the LABEL says as-needed => no derived reminder,
                         whatever frequency_type the proposer chose

G2 IS DELIBERATELY ASYMMETRIC (spec §4, amended 2026-07-28). `explicit_times`
strips on violation because a wrong time fires a wrong reminder and G4 will
supply a correct one anyway -- stripping loses nothing. `drug_name` and
`dosage` do NOT strip: they are compared over an OCR-confusable fold and,
if still unsupported, are KEPT and flagged. Rationale: nothing here
auto-commits (non-negotiable §0.1), so the protection was always the human
confirm, never the deletion. On the measured held-out case
`H10-ocr-noise-atorvastatin` (raw text `AT0RVASTATIN 2O MG`, truth
`atorvastatin`/`20mg`) a stripping guard would have deleted the CORRECT name
and dosage -- destroying value on exactly the noisy labels the LLM proposer
was selected to rescue -- and handed a tired senior a blank field to retype
off a label they may not read well. This is also the more MEDIC-faithful
reading: MEDIC's guards flag for pharmacist review; its 95.1% is a flagging
metric, not a deletion metric.

G4 REPLACES the LLM's own time derivation entirely. The 2026-07-28 probe
measured qwen2.5:7b's ONLY held-out miss as a derivation error (French BID
label -> 08:00+13:00 instead of 08:00+18:00), so derivation moved here where
it is a lookup table and cannot be wrong.

G6 IS THE ONLY GUARD THAT READS THE LABEL INSTEAD OF THE PROPOSAL (added
2026-07-30). A lookup table that cannot be wrong is still only as good as the
key it is given, and the key comes from the proposer. On label C of the
published eval set ("Take 1 tablet at bedtime as needed for pain") the
shipped sidecar proposer has been observed to answer THREE different ways:

    frequency_type=BEDTIME, explicit_times=[]         -> G4 derives 21:00
    frequency_type=BEDTIME, explicit_times=["21:00"]  -> plus an INVENTED time
    frequency_type=PRN,     explicit_times=["21:00"]  -> right word, wrong time

The first gives an as-needed NSAID a fixed nightly reminder with nothing
flagged. Nothing downstream of `frequency_type` can see it, because the
pipeline's own answer to "is this as-needed?" IS what went wrong.

AND THE CHOICE IS NOT STABLE, WHICH IS THE REAL ARGUMENT FOR THIS GUARD.
qwen2.5:7b at temperature 0 is stable WITHIN a burst of calls and unstable
ACROSS model loads: measured 2026-07-30, three consecutive calls returned
BEDTIME 3/3, and forty minutes later the identical prompt and text returned
PRN 3/3 -- each burst internally unanimous. So a 3-run protocol measures
burst agreement, not determinism, and no amount of prompt tuning or
re-measurement can retire this error class. Only a check that never consults
the classification can, which is what G6 is: it asks the label, and all three
observed answers above end with no reminder and a flagged medication.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from app.services import timing_parser
from app.services.prescription_parser import ParsedMedication

# --- Vocabulary -------------------------------------------------------------

FREQUENCY_ENUM: tuple[str, ...] = (
    "ONCE_DAILY", "BID", "TID", "QID", "BEDTIME", "WITH_MEALS",
    "PRN", "WEEKLY", "EVERY_N_HOURS", "TAPER", "UNKNOWN",
)

FLAG_NOT_IN_REFERENCE = "not_in_reference"
FLAG_NOT_ON_LABEL = "not_on_label"
FLAG_NEEDS_SCHEDULE = "needs_schedule"
FLAG_CONFLICT = "conflict"
FLAG_AS_NEEDED = "as_needed"

#: Flags that block `review_status='approved'` until the user edits or
#: explicitly confirms the field they refer to. `not_in_reference` and
#: `conflict` are informational (the reference is incomplete, and a conflict
#: is resolved by deleting the duplicate) -- they never block.
#:
#: `as_needed` is informational too, and deliberately so: it EXPLAINS why a
#: medication has no reminder times, while the blocking is done by the
#: `needs_schedule` that G6 forces alongside it. Making it block as well
#: would demand two separate acknowledgements for one fact.
BLOCKING_FLAGS: frozenset[str] = frozenset({FLAG_NOT_ON_LABEL, FLAG_NEEDS_SCHEDULE})

#: G4's canonical frequency -> reminder-times table. The ONLY place the app
#: turns a frequency word into a clock time.
FREQUENCY_TIMES: dict[str, list[str]] = {
    "ONCE_DAILY": ["08:00"],
    "BID": ["08:00", "18:00"],
    "TID": ["08:00", "13:00", "18:00"],
    "QID": ["08:00", "13:00", "18:00", "21:00"],
    "BEDTIME": ["21:00"],
    "WITH_MEALS": ["08:00", "13:00", "18:00"],
}

#: Frequencies that have no safe fixed daily time. The app NEVER invents
#: 08:00 for these -- it hands the decision to the user (non-negotiable §0.3;
#: the regex parser's silent default-morning is exactly the bug this closes).
NEEDS_SCHEDULE_FREQUENCIES: frozenset[str] = frozenset(
    {"PRN", "WEEKLY", "EVERY_N_HOURS", "TAPER", "UNKNOWN"}
)

#: G2's name-similarity floor, over the confusable fold. stdlib difflib --
#: no new dependency.
NAME_SIMILARITY_THRESHOLD = 0.85

_MIN_TOKEN_LEN = 3

# --- OCR-confusable normalization (G2) --------------------------------------
#
# Both sides of every comparison go through this, so a label that OCR read as
# `AT0RVASTATIN 2O MG` and a proposal that says `ATORVASTATIN 20 MG` collapse
# to the same string. Folds are one-directional into a single canonical
# character, which makes the relation symmetric: 0/O -> o, 1/l/I -> l,
# 5/S -> s, 8/B -> b, 2/Z -> z, and the classic ligature confusion rn -> m.

_CONFUSABLE = str.maketrans({
    "0": "o",
    "1": "l", "i": "l",
    "5": "s",
    "8": "b",
    "2": "z",
})
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# A bare 24-hour clock time printed on the label ("20:00"), excluding
# am/pm forms which `timing_parser.parse_specific_times` already handles --
# without the lookahead, "8:00 PM" would ALSO register a bogus "08:00".
_TWENTYFOUR_HOUR = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b(?!\s*[ap]\.?m\.?)", re.I)
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _fold(value: str) -> str:
    # "rn" -> "m" first: neither r nor n is itself remapped, so the order
    # only matters relative to case folding, which happens here.
    return value.lower().replace("rn", "m").translate(_CONFUSABLE)


def normalize_confusable(value: str) -> str:
    """Case/space/punctuation fold plus OCR-confusable character fold."""
    return _NON_ALNUM.sub("", _fold(value))


def _confusable_tokens(value: str) -> list[str]:
    return [token for token in _NON_ALNUM.split(_fold(value)) if token]


def value_supported_by_label(value: str | None, raw_text: str) -> bool:
    """True when `value` is plausibly printed on the label.

    Containment over the confusable fold first (cheap, catches the OCR-noise
    class); otherwise every significant token of the value must have a
    `SequenceMatcher` ratio >= NAME_SIMILARITY_THRESHOLD against some label
    token. Requiring EVERY token -- not the best one -- is what stops an
    invented strength riding along on a correct drug name.
    """
    if value is None or not str(value).strip():
        return True  # nothing proposed => nothing to invent
    normalized = normalize_confusable(str(value))
    if not normalized:
        return True
    haystack = normalize_confusable(raw_text)
    if normalized in haystack:
        return True

    label_tokens = _confusable_tokens(raw_text)
    if not label_tokens:
        return False
    value_tokens = [t for t in _confusable_tokens(str(value)) if len(t) >= _MIN_TOKEN_LEN]
    if not value_tokens:
        # Only trivially short tokens (e.g. "5 mg") and containment already
        # failed -- treat as unsupported rather than waving it through.
        return False
    for token in value_tokens:
        if token in haystack:
            continue
        best = max(
            (difflib.SequenceMatcher(None, token, label_token).ratio() for label_token in label_tokens),
            default=0.0,
        )
        if best < NAME_SIMILARITY_THRESHOLD:
            return False
    return True


def label_clock_times(raw_text: str) -> set[str]:
    """Every clock time LITERALLY printed on the label, in 24h "HH:MM"."""
    times = set(timing_parser.parse_specific_times(raw_text))
    for match in _TWENTYFOUR_HOUR.finditer(raw_text):
        times.add(f"{int(match.group(1)):02d}:{match.group(2)}")
    return times


# --- The proposal record ----------------------------------------------------

@dataclass
class MedicationProposal:
    """One proposed medication, proposer-agnostic.

    `explicit_times` is what the proposer claims is PRINTED on the label.
    `specific_times` is what the app will actually remind on -- written by
    G4 here and nowhere else.

    `as_needed` is written by G6 from the LABEL text, never from
    `frequency_type`. The two are independent on purpose: a label may say
    both "at bedtime" and "as needed", and each fact is kept.
    """

    drug_name: str
    dosage: str | None = None
    frequency_type: str = "UNKNOWN"
    explicit_times: list[str] = field(default_factory=list)
    with_food: bool = False
    frequency_text: str = ""
    time_slots: list[str] = field(default_factory=list)
    purpose: str | None = None
    max_daily_dose: int | None = None
    specific_times: list[str] = field(default_factory=list)
    as_needed: bool = False
    flags: list[str] = field(default_factory=list)

    def add_flag(self, flag: str) -> None:
        if flag not in self.flags:
            self.flags.append(flag)


def from_llm_medication(item: dict) -> MedicationProposal:
    """Sidecar `/rx/extract` entry -> proposal. Shape-tolerant: the sidecar
    already coerces types, this only has to survive a surprise."""
    times = item.get("explicit_times")
    return MedicationProposal(
        drug_name=str(item.get("drug_name") or "").strip() or "Unknown medication",
        dosage=(str(item["dosage"]).strip() or None) if item.get("dosage") else None,
        frequency_type=str(item.get("frequency_type") or "UNKNOWN").upper(),
        explicit_times=[str(t) for t in times] if isinstance(times, list) else [],
        with_food=bool(item.get("with_food")),
    )


def from_parsed_medication(med: ParsedMedication) -> MedicationProposal:
    """Regex `ParsedMedication` -> proposal.

    NOTE the deliberate discard: `med.specific_times` is NOT carried over.
    Those are mostly *derived* by the regex parser (including its silent
    default-morning), and G4 owns derivation on this path. Only genuinely
    explicit clock times found in the medication's own instruction text
    survive as `explicit_times`; G2 then re-verifies even those.
    """
    return MedicationProposal(
        drug_name=med.drug_name,
        dosage=med.dosage,
        frequency_type=(med.frequency_type or "UNKNOWN").upper(),
        explicit_times=timing_parser.parse_specific_times(med.frequency_text or ""),
        with_food=bool(med.with_food),
        frequency_text=med.frequency_text,
        time_slots=list(med.time_slots),
        purpose=med.purpose,
        max_daily_dose=med.max_daily_dose,
    )


# --- The guards -------------------------------------------------------------

def _g3_schema(med: MedicationProposal) -> None:
    if med.frequency_type not in FREQUENCY_ENUM:
        med.frequency_type = "UNKNOWN"
    med.explicit_times = [t for t in med.explicit_times if _HHMM.match(str(t).strip())]


def _g2_no_invention(med: MedicationProposal, raw_text: str) -> None:
    printed_times = label_clock_times(raw_text)
    if med.explicit_times and not set(med.explicit_times) <= printed_times:
        # STRIP -- safe by construction, G4 re-supplies from frequency_type.
        med.explicit_times = []
        med.add_flag(FLAG_NOT_ON_LABEL)

    # KEEP-AND-FLAG -- never null. See the module docstring.
    if not value_supported_by_label(med.drug_name, raw_text):
        med.add_flag(FLAG_NOT_ON_LABEL)
    if not value_supported_by_label(med.dosage, raw_text):
        med.add_flag(FLAG_NOT_ON_LABEL)


#: Day-part buckets for DISPLAY only (the slot badges on My Medications and
#: the dashboard schedule). Identical boundaries to the frontend's
#: `slotForTime` in DashboardPage.tsx.
_SLOT_BOUNDS = (("morning", 5, 12), ("afternoon", 12, 17), ("evening", 17, 20))


def _slots_for_times(times: list[str]) -> list[str]:
    order = ["morning", "afternoon", "evening", "night"]
    found: set[str] = set()
    for value in times:
        try:
            hour = int(str(value).split(":")[0])
        except (ValueError, IndexError):
            continue
        found.add(next((name for name, lo, hi in _SLOT_BOUNDS if lo <= hour < hi), "night"))
    return [slot for slot in order if slot in found]


# --- G6: the as-needed truth check ------------------------------------------

def _label_lines(raw_text: str) -> list[str]:
    return [line for line in (raw_text or "").splitlines() if line.strip()]


def as_needed_windows(medications: list[MedicationProposal], raw_text: str) -> list[str]:
    """The slice of label text that belongs to each medication.

    Scoping matters more than the check itself. A multi-medication label
    carries "as needed" for ONE of its medications: on the measured label C,
    reading the phrase against the whole dump would also strip metformin's
    twice-daily reminder -- trading an invented reminder for a lost one.

    Each proposal is located by its own name on a label LINE, over the same
    OCR-confusable fold G2 compares with, and owns the lines from there up
    to the next located proposal.

    TWO DELIBERATE FALLBACKS TO THE WHOLE TEXT, both in the conservative
    direction:
      * a SINGLE medication -- there is nothing to disambiguate, and the
        instruction line is not guaranteed to follow the name (it can
        precede it, and on the demo one-liner there are no lines at all);
      * a proposal whose name cannot be located -- an unparseable label
        must not silently narrow the search for the phrase.
    Over-attributing "as needed" withholds a reminder and asks the user;
    under-attributing invents one. Only the second is a safety event.
    """
    if len(medications) <= 1:
        return [raw_text] * len(medications)

    lines = _label_lines(raw_text)
    folded = [normalize_confusable(line) for line in lines]

    located: dict[int, int] = {}
    claimed: set[int] = set()
    for position, med in enumerate(medications):
        needle = normalize_confusable(med.drug_name)
        if not needle:
            continue
        for index, haystack in enumerate(folded):
            if index in claimed or not haystack:
                continue
            if needle in haystack:
                located[position] = index
                claimed.add(index)
                break

    boundaries = sorted(located.values())
    windows: list[str] = []
    for position in range(len(medications)):
        start = located.get(position)
        if start is None:
            windows.append(raw_text)
            continue
        later = [b for b in boundaries if b > start]
        stop = later[0] if later else len(lines)
        windows.append("\n".join(lines[start:stop]))
    return windows


def _g6_as_needed(medications: list[MedicationProposal], raw_text: str) -> None:
    """Ask the LABEL whether each medication is as-needed, and mark it.

    This is the only guard that does not read the proposal. See the module
    docstring for the measured case; the structural point is that an
    acceptance invariant phrased over `frequency_type` ("no PRN medication
    may carry a reminder time") reports zero offenders on label C -- and is
    right to, because the pipeline classified it BEDTIME. An invariant over
    a system's own classification is blind precisely when the classification
    is the defect.

    `frequency_type` is NOT rewritten. The label printed two facts, "at
    bedtime" and "as needed", and both are worth keeping: the day-part stays
    visible to the user while the reminder is withheld by G4.
    """
    for med, window in zip(medications, as_needed_windows(medications, raw_text)):
        if timing_parser.has_as_needed(window):
            med.as_needed = True
            med.add_flag(FLAG_AS_NEEDED)


def _g4_derive_times(med: MedicationProposal) -> None:
    if med.as_needed:
        # G6 override. No fixed reminder may be derived for a medication the
        # LABEL calls as-needed, from a frequency word or from a printed
        # clock time -- on an as-needed medication a printed time is a
        # ceiling ("no more often than every 6 hours"), not a schedule.
        # `needs_schedule` blocks approval, so the user either enters real
        # times or confirms there are none; nothing is silently lost.
        med.specific_times = []
        med.add_flag(FLAG_NEEDS_SCHEDULE)
    elif med.explicit_times:
        med.specific_times = sorted(set(med.explicit_times))
    elif med.frequency_type in NEEDS_SCHEDULE_FREQUENCIES:
        med.specific_times = []
        med.add_flag(FLAG_NEEDS_SCHEDULE)
    else:
        med.specific_times = list(FREQUENCY_TIMES.get(med.frequency_type, []))
        if not med.specific_times:
            # Defensive: an enum member with no table entry would otherwise
            # silently yield no reminder at all with no flag to say so.
            med.add_flag(FLAG_NEEDS_SCHEDULE)

    # `time_slots` is a DISPLAY field (the slot badges), and it is recomputed
    # from the derived times for BOTH proposers rather than carried over from
    # whichever one spoke. The LLM proposer has no notion of slots at all, so
    # without this an LLM-parsed medication rendered with no badges while the
    # identical regex-parsed one rendered with three -- a visible, purely
    # cosmetic difference that would make the swappable-proposer claim false
    # to a user's eye.
    med.time_slots = _slots_for_times(med.specific_times)


def _g5_conflict(medications: list[MedicationProposal]) -> None:
    by_name: dict[str, list[MedicationProposal]] = {}
    for med in medications:
        by_name.setdefault(normalize_confusable(med.drug_name), []).append(med)
    for group in by_name.values():
        if len(group) < 2:
            continue
        for med in group:
            med.add_flag(FLAG_CONFLICT)

    # A single medication can also carry conflicting dosages if a proposer
    # emitted the same drug twice with different strengths -- covered above --
    # or if one proposal's own dosage disagrees with a strength printed in
    # its name (e.g. name "METFORMIN 500 MG", dosage "850 mg").
    for med in medications:
        if not med.dosage:
            continue
        name_doses = {
            normalize_confusable(m.group(1))
            for m in re.finditer(r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu))\b", med.drug_name, re.I)
        }
        if name_doses and normalize_confusable(med.dosage) not in name_doses:
            med.add_flag(FLAG_CONFLICT)


def apply(medications: list[MedicationProposal], raw_text: str) -> list[MedicationProposal]:
    """Run G2-G6 in order and return the same list, mutated in place.

    G1 (catalog) is not here: it needs the reference lookup the route
    already performs for DIN suggestions, so it is applied by
    `flag_not_in_reference` with those results rather than issuing a second
    round of sidecar calls.

    G6 runs BETWEEN the per-medication passes, not inside them: derivation
    must already know whether the label calls a medication as-needed, and
    the windowing needs the whole proposal list to give each medication its
    own slice of a multi-medication label.
    """
    for med in medications:
        _g3_schema(med)
        _g2_no_invention(med, raw_text)
    _g6_as_needed(medications, raw_text)
    for med in medications:
        _g4_derive_times(med)
    _g5_conflict(medications)
    return medications


def flag_not_in_reference(med: MedicationProposal, suggestions: list[dict]) -> None:
    """G1 catalog cross-check, using the DIN suggestions the route already
    fetched. No hit => flag; the medication is still shown, because the
    reference tier is incomplete by construction (11,609 marketed human
    DINs, and even that misses OTC/natural-health products)."""
    if not suggestions:
        med.add_flag(FLAG_NOT_IN_REFERENCE)


# --- Approval gate (used by PATCH /prescriptions/{id}) ----------------------

def blocking_flags(flags: list[str] | None) -> list[str]:
    return [f for f in (flags or []) if f in BLOCKING_FLAGS]


def unresolved_blocking_flags(
    flags: list[str] | None,
    *,
    specific_times: list[str] | None,
    confirmed_flags: list[str] | None,
) -> list[str]:
    """Which blocking flags still stand in the way of approval.

    A flag is resolved either by the resulting STATE (`needs_schedule` is
    resolved once the medication actually has reminder times) or by an
    EXPLICIT acknowledgement from the user (`confirmed_flags`) -- which is
    what the review screen's per-field "I checked this against my label"
    confirm sends, and the only way to approve a PRN medication that
    legitimately has no fixed times.
    """
    confirmed = set(confirmed_flags or [])
    unresolved: list[str] = []
    for flag in blocking_flags(flags):
        if flag in confirmed:
            continue
        if flag == FLAG_NEEDS_SCHEDULE and specific_times:
            continue
        unresolved.append(flag)
    return unresolved
