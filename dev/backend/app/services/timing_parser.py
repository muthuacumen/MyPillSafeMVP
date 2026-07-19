"""Regex-based prescription frequency parser — no ML, per build spec."""
import re

_PHRASE_RULES: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"\bfour times?\s*(?:a\s+day|daily)\b|\bqid\b", re.I), ["morning", "afternoon", "evening", "night"]),
    (re.compile(r"\bthree times?\s*(?:a\s+day|daily)\b|\btid\b", re.I), ["morning", "afternoon", "evening"]),
    (re.compile(r"\btwice\s*(?:a\s+day|daily)\b|\bbid\b", re.I), ["morning", "evening"]),
    (re.compile(r"\bat (bedtime|night)\b", re.I), ["night"]),
    (re.compile(r"\bwith meals?\b", re.I), ["morning", "afternoon", "evening"]),
    (re.compile(r"\bonce\s*(?:a\s+day|daily)\b|\bod\b", re.I), ["morning"]),
    (re.compile(r"\bmorning\b", re.I), ["morning"]),
    (re.compile(r"\bafternoon\b", re.I), ["afternoon"]),
    (re.compile(r"\bevening\b", re.I), ["evening"]),
]

_TIME_PATTERN = re.compile(
    r"\b(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*([ap]\.?m\.?)\b", re.I
)


def _normalize_time(hour: int, minute: int, meridiem: str) -> str:
    meridiem = meridiem.lower().replace(".", "")
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def parse_specific_times(raw_text: str) -> list[str]:
    """Extract explicit clock times, e.g. '8am' / '8:00 PM' -> ['08:00', '20:00']."""
    times: list[str] = []
    for match in _TIME_PATTERN.finditer(raw_text):
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        times.append(_normalize_time(hour, minute, match.group(3)))
    return times


def parse_time_slots(raw_text: str) -> list[str]:
    """Map frequency phrases to coarse day-part slots, in display order."""
    order = ["morning", "afternoon", "evening", "night"]
    found: set[str] = set()
    for pattern, slots in _PHRASE_RULES:
        if pattern.search(raw_text):
            found.update(slots)
            break
    return [slot for slot in order if slot in found]


def parse_frequency(raw_text: str) -> tuple[list[str], list[str]]:
    """Return (time_slots, specific_times) parsed from raw OCR frequency text."""
    specific_times = parse_specific_times(raw_text)
    time_slots = parse_time_slots(raw_text)
    if not time_slots and not specific_times:
        time_slots = ["morning"]
    return time_slots, specific_times


_PRN_PATTERN = re.compile(r"\bas\s+needed\b|\bprn\b", re.I)

_CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfour times?\s*(?:a\s+day|daily)\b|\bqid\b", re.I), "QID"),
    (re.compile(r"\bthree times?\s*(?:a\s+day|daily)\b|\btid\b", re.I), "TID"),
    (re.compile(r"\btwice\s*(?:a\s+day|daily)\b|\bbid\b", re.I), "BID"),
    (re.compile(r"\bat (bedtime|night)\b", re.I), "BEDTIME"),
    (re.compile(r"\bwith meals?\b|\bwith food\b", re.I), "WITH_MEALS"),
    (re.compile(r"\bonce\s*(?:a\s+day|daily)\b|\bod\b", re.I), "ONCE_DAILY"),
]


def classify_frequency(raw_text: str) -> str:
    """Tag the semantic frequency category — PRN takes priority over any
    co-occurring day-part wording (e.g. "every 6 hours as needed")."""
    if _PRN_PATTERN.search(raw_text):
        return "PRN"
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(raw_text):
            return category
    return "UNKNOWN"
