"""Splits raw OCR text from a (possibly multi-medication) prescription
photo into one structured ParsedMedication per detected Rx block.

Falls back to the single-medication behaviour (first line as drug name,
frequency parsed over the whole text) when no "RX n" markers are found, so
OCR_PIPELINE_ENABLED=false (_DEMO_RAW_TEXT) and any photo without explicit
Rx markers keep working unchanged.

Real pharmacy labels (the common case in production) never carry "RX n"
markers, so they always go through the fallback path below. Two hardening
rules apply there (FixbySonnet1 Task 1, Bug #1):

  * `drug_name` must never be a pharmacy/clinic header line -- header/noise
    lines are skipped in favour of the first line that looks like a
    medication (has a dosage unit), or else the first non-header line.
  * `frequency_text` must be instruction-like text, not the entire OCR
    dump -- only lines carrying a timing/instruction signal are kept, so a
    long, garbled real-world label can never overflow the DB column (see
    `_clamp` below, which is also a hard backstop regardless of text shape).
"""
import re
from dataclasses import dataclass

from app.services import timing_parser

_RX_MARKER = re.compile(r"^\s*RX\s*\d+\s*$", re.I | re.M)
# Both boundaries matter: without the trailing \b, "g" alone (from the
# mg/mcg/ml/g/iu alternation) false-matches inside postal codes like
# "N2L 3G1" (the "3G" substring). Without the LEADING \b too, "N2G 1A1"
# (a Canadian postal code split by a space, as in a real clinic address)
# still false-matches on "2G " -- the "2" isn't at a word boundary inside
# "N2G", so requiring \b immediately before the digit run rules that out:
# a real dosage digit run is never glued to a preceding letter like that.
_DOSAGE = re.compile(r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu)\b)", re.I)
_WITH_FOOD = re.compile(r"\bwith (meals?|food)\b", re.I)
_MAX_DOSE = re.compile(
    r"(?:do not exceed|maximum|max)\s+(\d+)\s*(?:tablets?|capsules?|doses?)", re.I
)
_PURPOSE = re.compile(r"\bfor\s+([a-z][a-z ]{1,40}?)(?=[.,;:\n—-]|$)", re.I)

# Column limits (app/models/prescription.py) -- every ParsedMedication field
# must fit by construction so a DB-length crash from parsed OCR text is
# impossible regardless of what OCR returns (Task 1, root cause: a real
# pharmacy label's full-dump frequency_text exceeded String(255) and raised
# an unhandled StringDataRightTruncationError on INSERT).
_LIMITS = {
    "drug_name": 255,
    "dosage": 100,
    "frequency_text": 255,
    "frequency_type": 30,
    "purpose": 100,
}

# Header/noise lines that must never be selected as a drug name -- pharmacy
# and clinic letterheads, contact details, and address fragments.
#
# Every word-like alternative is \b-bounded. Without boundaries the bare
# substring "tel" rejected real drug names that merely CONTAIN it --
# TELmisartan and monTELukast are both top-50 Canadian prescriptions, and
# both were being discarded as "header noise" (FixbySonnet2 Defect B).
# `dr\.` / `www\.` keep a leading \b but end in a literal dot, and `@` is
# punctuation, so none of those three take a trailing boundary.
_HEADER_NOISE = re.compile(
    r"\b(?:pharmacy|pharmacies|clinic|hospital|health\s+(?:centre|center)|medical|"
    r"phone|fax|tel|telephone|postal|address)\b"
    r"|\bdr\.|\bwww\.|@"
    # Canadian pharmacy/retail chains -- defence in depth. The dosage-unit
    # preference in _select_drug_name already handles the common case; this
    # only helps when no candidate line carries a dosage. Deliberately
    # conservative: a false "this is a header" on a real drug line is worse
    # than missing a header.
    r"|\b(?:shoppers\s+drug\s+mart|rexall|london\s+drugs|jean\s+coutu|pharmaprix|"
    r"uniprix|familiprix|guardian\s+drugs|medicine\s+shoppe|costco|walmart|"
    r"sobeys|safeway|loblaw)\b",
    re.I,
)
_MOSTLY_DIGITS_PUNCT = re.compile(r"^[\d\s.,\-/#:()]+$")

# A name-candidate line's trailing "- Dr. X, Refills: N" tail is separated
# by whitespace (" - ") or an em/en dash. A hyphen inside a token is part of
# the drug name -- see _clean_candidate.
_NAME_TAIL_SEP = re.compile(r"\s+[-–—]\s+|\s*[–—]\s*")

# Timing/instruction vocabulary -- a line must contain one of these (or an
# explicit clock time, see _select_frequency_text) to be considered
# instruction-like and kept in frequency_text. Deliberately narrow to
# timing/dosing-schedule words (not "take"/"tablets"/"capsules", which also
# appear on the drug-name line itself and would defeat the header/name
# separation this is meant to provide).
#
# NOTE: this list covers timing_parser's PHRASE and CATEGORY rules only --
# it does NOT cover explicit clock times ("8:00 PM"), which live in
# timing_parser.TIME_PATTERN. _select_frequency_text tests both, reusing
# that pattern rather than duplicating it so the two can never drift
# (FixbySonnet2 Defect C: a clock-time-only line was dropped here, and the
# evening dose was silently lost).
_INSTRUCTION_SIGNAL = re.compile(
    r"\bdaily\b|\btwice\b|\bonce\b|\b\d+\s*times?\b|\bthree times\b|\bfour times\b|"
    r"\bbid\b|\btid\b|\bqid\b|\bod\b|"
    r"\bmorning\b|\bafternoon\b|\bevening\b|\bnight\b|\bbedtime\b|"
    r"\bwith (meals?|food)\b|\bevery\s+\d+(?:\s*-\s*\d+)?\s*hours?\b|\bhourly\b|"
    r"\bas needed\b|\bprn\b",
    re.I,
)

_DEFAULT_SLOT_TIME = {
    "morning": "08:00",
    "afternoon": "13:00",
    "evening": "18:00",
    "night": "21:00",
}


def _clamp(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    limit = _LIMITS[field_name]
    return value[:limit]


@dataclass
class ParsedMedication:
    drug_name: str
    dosage: str | None
    frequency_text: str
    frequency_type: str
    time_slots: list[str]
    specific_times: list[str]
    with_food: bool = False
    purpose: str | None = None
    max_daily_dose: int | None = None

    def __post_init__(self) -> None:
        # Bound-by-construction: no ParsedMedication can ever carry a string
        # field too long for its DB column, regardless of what OCR/parsing
        # produced upstream.
        self.drug_name = _clamp(self.drug_name, "drug_name") or "Unknown medication"
        self.dosage = _clamp(self.dosage, "dosage")
        self.frequency_text = _clamp(self.frequency_text, "frequency_text") or ""
        self.frequency_type = _clamp(self.frequency_type, "frequency_type") or "UNKNOWN"
        self.purpose = _clamp(self.purpose, "purpose")


def _derive_specific_times(time_slots: list[str], explicit_times: list[str]) -> list[str]:
    if explicit_times:
        return sorted(set(explicit_times))
    return [_DEFAULT_SLOT_TIME[s] for s in time_slots if s in _DEFAULT_SLOT_TIME]


def _is_header_noise(line: str) -> bool:
    if len(line) < 3:
        return True
    if _MOSTLY_DIGITS_PUNCT.match(line):
        return True
    if _HEADER_NOISE.search(line):
        return True
    return False


def _clean_candidate(line: str) -> str:
    """Cut a trailing '- Dr. X, Refills: N' style tail off a name-candidate
    line, WITHOUT breaking hyphenated drug names.

    A tail separator is whitespace-delimited (" - ") or an em/en dash; a
    hyphen INSIDE a token belongs to the drug name. The previous bare
    `.split("-")[0]` truncated the dominant Canadian generic naming
    convention -- APO-METFORMIN -> "APO", CO-TRIMOXAZOLE -> "CO",
    NITRO-DUR -> "NITRO" (12 of 24 realistic names measured) -- and with the
    name it destroyed the dosage signal that _select_drug_name ranks on,
    which is how a pharmacy header came to win instead (FixbySonnet2
    Defect A)."""
    return _NAME_TAIL_SEP.split(line, maxsplit=1)[0].strip()


def _select_drug_name(lines: list[str]) -> str:
    """Pick the best drug-name candidate from raw OCR lines: never a
    pharmacy/clinic header, prefer a line with a dosage unit, else the
    first non-header line, else the existing 'Unknown medication' fallback."""
    candidates = [c for ln in lines if (c := _clean_candidate(ln)) and not _is_header_noise(c)]
    for c in candidates:
        if _DOSAGE.search(c):
            return c
    if candidates:
        return candidates[0]
    return "Unknown medication"


def _select_frequency_text(lines: list[str]) -> str:
    """Keep only instruction-like lines (timing/dosing vocabulary OR an
    explicit clock time), joined and capped at 255 chars. Real-label noise
    (letterhead, addresses, refill/DIN footers) never makes it into
    frequency_text.

    timing_parser.TIME_PATTERN is reused rather than re-expressed here so a
    clock-time-only line ("Take 1 tablet at 8:00 AM and 8:00 PM") is kept,
    and so this test and the parser can never drift apart."""
    instruction_lines = [
        ln for ln in lines
        if _INSTRUCTION_SIGNAL.search(ln) or timing_parser.TIME_PATTERN.search(ln)
    ]
    return " ".join(instruction_lines)


# --- Multi-medication segmentation of a no-marker label --------------------
#
# A real pharmacy/clinic label never carries "RX n" markers, so a label
# listing several medications used to collapse into a SINGLE prescription
# record and every medication after the first was silently lost. Two anchor
# strategies run in priority order:
#
#   1. ENUMERATION -- "1." / "2)" list items, the shape a prescriber's Rx
#      list actually uses (and the shape of the synthetic test document).
#   2. DOSAGE LINES -- only when there is no enumeration: a name-like line
#      carrying a strength, followed by its own directions.
#
# Both require at least TWO surviving anchors, so a single-medication label
# keeps the existing single-record behaviour exactly and can never grow a
# phantom second record. Every anchor is validated before it is trusted,
# because the two error directions are not equally bad: a missed split loses
# a medication, but a phantom split invents a prescription the patient was
# never given and schedules reminders for it. When in doubt, do not split.

_ENUM_MARKER = re.compile(r"^\s*\d{1,2}\s*[.)]\s+(?=\S)")

# Directions rather than a name. Also used to reject an instruction line
# from ever being taken AS a name.
_TAKE_VERB = re.compile(
    r"^\s*(?:take|give|apply|use|inject|inhale|instil|swallow|sig\b|directions?\b)", re.I
)

# Quantity / limit / footer vocabulary. Such a line may well carry a
# strength ("do not exceed 4000 mg daily", "total 5 mg per day") but is
# never a medication name -- these are the phantom-record traps.
_NOT_A_NAME = re.compile(
    r"\b(?:exceed|maximum|max|total|qty|quantity|refills?|din|lot|exp|"
    r"dispense|counsell?ing|notes?)\b",
    re.I,
)


def _is_instruction_line(line: str) -> bool:
    return bool(
        _TAKE_VERB.match(line)
        or _INSTRUCTION_SIGNAL.search(line)
        or timing_parser.TIME_PATTERN.search(line)
    )


def _is_name_like(line: str) -> bool:
    """A plausible medication-name line: carries a strength, is not header
    noise, and is neither directions nor a quantity/limit/footer line."""
    return bool(
        _DOSAGE.search(line)
        and not _is_header_noise(line)
        and not _NOT_A_NAME.search(line)
        and not _is_instruction_line(line)
    )


def _owns_instructions(lines: list[str], start: int, stop: int) -> bool:
    """True if this anchor has at least one directions line of its own
    before the next candidate anchor."""
    return any(_is_instruction_line(lines[i]) for i in range(start + 1, stop))


def _enumeration_anchors(lines: list[str]) -> list[int]:
    marked = [i for i, ln in enumerate(lines) if _ENUM_MARKER.match(ln)]
    anchors: list[int] = []
    for pos, i in enumerate(marked):
        body = _ENUM_MARKER.sub("", lines[i]).strip()
        if not body or _is_header_noise(body) or _is_instruction_line(body):
            continue
        # A numbered counselling note ("1. Avoid alcohol") carries no
        # strength AND owns no directions; a real Rx list item has at least
        # one of the two.
        stop = marked[pos + 1] if pos + 1 < len(marked) else len(lines)
        if _DOSAGE.search(body) or _owns_instructions(lines, i, stop):
            anchors.append(i)
    return anchors


def _dosage_anchors(lines: list[str]) -> list[int]:
    candidates = [i for i, ln in enumerate(lines) if _is_name_like(ln)]
    anchors: list[int] = []
    for pos, i in enumerate(candidates):
        stop = candidates[pos + 1] if pos + 1 < len(candidates) else len(lines)
        if _owns_instructions(lines, i, stop):
            anchors.append(i)
    return anchors


def _split_anchors(lines: list[str]) -> list[int]:
    """Anchor line indices for a multi-medication label, or [] to keep the
    single-record behaviour."""
    for anchors in (_enumeration_anchors(lines), _dosage_anchors(lines)):
        if len(anchors) >= 2:
            return anchors
    return []


def _split_into_medications(lines: list[str]) -> list[ParsedMedication]:
    """Segment a no-marker label into one ParsedMedication per detected
    medication. Returns [] when the label is (or looks like) a single
    medication, so the caller keeps its existing single-record path."""
    anchors = _split_anchors(lines)
    if not anchors:
        return []
    medications: list[ParsedMedication] = []
    for pos, start in enumerate(anchors):
        stop = anchors[pos + 1] if pos + 1 < len(anchors) else len(lines)
        block = [_ENUM_MARKER.sub("", lines[start]).strip(), *lines[start + 1: stop]]
        # Everything before the first anchor -- letterhead, patient block,
        # prescriber details -- is dropped by construction, which is the
        # same header/name separation _select_drug_name has to earn by
        # ranking. Blocks are parsed by the RX-marker path's own
        # _parse_block, so both multi-medication paths behave identically.
        if (med := _parse_block("\n".join(block))) is not None:
            medications.append(med)
    # Only accept a genuine split; anything less falls back to one record.
    return medications if len(medications) >= 2 else []


def _parse_block(block: str) -> ParsedMedication | None:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return None

    name_line = lines[0]
    dosage_match = _DOSAGE.search(name_line)
    dosage = dosage_match.group(1).replace(" ", "") if dosage_match else None
    drug_name = (name_line[: dosage_match.start()] if dosage_match else name_line).strip(" -—")
    drug_name = drug_name.split("(")[0].strip() or "Unknown medication"

    instruction_text = " ".join(lines[1:]) or name_line
    instruction_text = re.split(r"\bQty\b", instruction_text, maxsplit=1, flags=re.I)[0].strip()

    frequency_type = timing_parser.classify_frequency(instruction_text)
    if frequency_type == "PRN":
        time_slots: list[str] = []
        specific_times: list[str] = []
    else:
        time_slots, explicit_times = timing_parser.parse_frequency(instruction_text)
        specific_times = _derive_specific_times(time_slots, explicit_times)

    max_match = _MAX_DOSE.search(instruction_text)
    purpose_match = _PURPOSE.search(instruction_text)

    return ParsedMedication(
        drug_name=drug_name,
        dosage=dosage,
        frequency_text=instruction_text,
        frequency_type=frequency_type,
        time_slots=time_slots,
        specific_times=specific_times,
        with_food=bool(_WITH_FOOD.search(instruction_text)),
        purpose=purpose_match.group(1).strip() if purpose_match else None,
        max_daily_dose=int(max_match.group(1)) if max_match else None,
    )


def parse_medications(raw_text: str) -> list[ParsedMedication]:
    if not raw_text.strip():
        return [ParsedMedication("Unknown medication", None, "", "UNKNOWN", ["morning"], ["08:00"])]

    markers = list(_RX_MARKER.finditer(raw_text))
    if not markers:
        # Real-label fallback (no "RX n" markers -- the common case for a
        # genuine pharmacy label, and also _DEMO_RAW_TEXT's shape).
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

        # A label listing several medications yields one record each; a
        # single-medication label returns [] here and falls through to the
        # unchanged single-record path below.
        if medications := _split_into_medications(lines):
            return medications

        drug_name = _select_drug_name(lines)
        # What we STORE and what we PARSE are deliberately decoupled. The
        # clamp exists because a full OCR dump overflowed String(255), so
        # the stored/displayed text stays filtered + clamped. Schedule
        # parsing has no such constraint -- it emits short enums and small
        # lists -- so it reads the FULL raw text, as it did before the
        # instruction filter was introduced. Filtering here silently lost
        # doses: a clock-time line that the filter dropped took the 8 PM
        # dose with it (FixbySonnet2 Defect C).
        frequency_text = _select_frequency_text(lines)
        frequency_type = timing_parser.classify_frequency(raw_text)
        if frequency_type == "PRN":
            # An as-needed medication has no dose times, so it must not be
            # given any -- the same rule _parse_block has always applied on
            # the RX-marker path. Without this, an as-needed painkiller
            # parsed from a real label acquired a fixed daily reminder
            # (measured: PRN with specific_times=['21:00']) and the two
            # parse paths disagreed about identical wording.
            time_slots: list[str] = []
            specific_times: list[str] = []
        else:
            time_slots, explicit_times = timing_parser.parse_frequency(raw_text)
            specific_times = _derive_specific_times(time_slots, explicit_times)
        return [ParsedMedication(
            drug_name=drug_name,
            dosage=None,
            frequency_text=frequency_text,
            frequency_type=frequency_type,
            time_slots=time_slots,
            specific_times=specific_times,
        )]

    blocks = [
        raw_text[m.end(): markers[i + 1].start() if i + 1 < len(markers) else len(raw_text)]
        for i, m in enumerate(markers)
    ]
    medications = [med for b in blocks if (med := _parse_block(b)) is not None]
    return medications or [
        ParsedMedication("Unknown medication", None, raw_text, "UNKNOWN", ["morning"], ["08:00"])
    ]
