"""Splits raw OCR text from a (possibly multi-medication) prescription
photo into one structured ParsedMedication per detected Rx block.

Falls back to the single-medication behaviour (first line as drug name,
frequency parsed over the whole text) when no "RX n" markers are found, so
OCR_PIPELINE_ENABLED=false (_DEMO_RAW_TEXT) and any photo without explicit
Rx markers keep working unchanged.
"""
import re
from dataclasses import dataclass

from app.services import timing_parser

_RX_MARKER = re.compile(r"^\s*RX\s*\d+\s*$", re.I | re.M)
_DOSAGE = re.compile(r"(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu))", re.I)
_WITH_FOOD = re.compile(r"\bwith (meals?|food)\b", re.I)
_MAX_DOSE = re.compile(
    r"(?:do not exceed|maximum|max)\s+(\d+)\s*(?:tablets?|capsules?|doses?)", re.I
)
_PURPOSE = re.compile(r"\bfor\s+([a-z][a-z ]{1,40}?)(?=[.,;:\n—-]|$)", re.I)

_DEFAULT_SLOT_TIME = {
    "morning": "08:00",
    "afternoon": "13:00",
    "evening": "18:00",
    "night": "21:00",
}


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


def _derive_specific_times(time_slots: list[str], explicit_times: list[str]) -> list[str]:
    if explicit_times:
        return sorted(set(explicit_times))
    return [_DEFAULT_SLOT_TIME[s] for s in time_slots if s in _DEFAULT_SLOT_TIME]


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
        # Unchanged single-medication fallback (today's exact behaviour).
        drug_name = raw_text.splitlines()[0].split("—")[0].split("-")[0].strip() or "Unknown medication"
        time_slots, explicit_times = timing_parser.parse_frequency(raw_text)
        return [ParsedMedication(
            drug_name=drug_name,
            dosage=None,
            frequency_text=raw_text,
            frequency_type=timing_parser.classify_frequency(raw_text),
            time_slots=time_slots,
            specific_times=_derive_specific_times(time_slots, explicit_times),
        )]

    blocks = [
        raw_text[m.end(): markers[i + 1].start() if i + 1 < len(markers) else len(raw_text)]
        for i, m in enumerate(markers)
    ]
    medications = [med for b in blocks if (med := _parse_block(b)) is not None]
    return medications or [
        ParsedMedication("Unknown medication", None, raw_text, "UNKNOWN", ["morning"], ["08:00"])
    ]
