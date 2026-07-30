"""Regex-based prescription frequency parser — no ML, per build spec."""
import re

# Frequency wording, in priority order -- the FIRST match wins, so the
# higher-count rules must stay above the lower-count ones ("three times
# daily" also contains "daily", which the ONCE_DAILY rule would otherwise
# claim).
#
# Digit forms ("2 times a day") and "per day" are accepted alongside the
# word forms: a real label writes the count either way, and only the word
# forms were recognised, so "Take 1 tablet 2 times a day" fell through to
# UNKNOWN + the default-morning slot -- i.e. the evening dose was dropped
# from the schedule. Word and digit alternatives are kept in one rule each
# so the two can never disagree about which slots a count maps to.
_COUNT_SUFFIX = r"\s*(?:a\s+day|per\s+day|daily)\b"

_PHRASE_RULES: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(rf"\b(?:four|4)\s*times?{_COUNT_SUFFIX}|\bqid\b", re.I), ["morning", "afternoon", "evening", "night"]),
    (re.compile(rf"\b(?:three|3)\s*times?{_COUNT_SUFFIX}|\btid\b", re.I), ["morning", "afternoon", "evening"]),
    (re.compile(rf"\btwice{_COUNT_SUFFIX}|\b(?:two|2)\s*times?{_COUNT_SUFFIX}|\bbid\b", re.I), ["morning", "evening"]),
    (re.compile(r"\bat (bedtime|night)\b", re.I), ["night"]),
    (re.compile(r"\bwith meals?\b", re.I), ["morning", "afternoon", "evening"]),
    (re.compile(rf"\bonce{_COUNT_SUFFIX}|\b(?:one|1)\s*times?{_COUNT_SUFFIX}|\bod\b", re.I), ["morning"]),
    (re.compile(r"\bmorning\b", re.I), ["morning"]),
    (re.compile(r"\bafternoon\b", re.I), ["afternoon"]),
    (re.compile(r"\bevening\b", re.I), ["evening"]),
]

TIME_PATTERN = re.compile(
    r"\b(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*([ap]\.?m\.?)\b", re.I
)
# Back-compat alias: kept private-named so any existing internal callers
# (and external callers that imported the "private" name before it was
# made public) keep working unchanged.
_TIME_PATTERN = TIME_PATTERN


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

# Same order and the same digit/"per day" acceptance as _PHRASE_RULES
# above: the COUNT rules must agree between the two lists, or a label could
# get BID slots with an UNKNOWN category (or vice versa).
#
# The two lists are NOT identical elsewhere and deliberately stay that way
# for now: this list also categorises "with food", while _PHRASE_RULES maps
# only "with meals" to slots. Adding "with food" there would make it match
# ahead of the once-daily rule, turning "once daily with food" into three
# slots -- a worse bug than the one it fixes. Correcting that needs the
# rule ORDER revisited, which is its own change.
_CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b(?:four|4)\s*times?{_COUNT_SUFFIX}|\bqid\b", re.I), "QID"),
    (re.compile(rf"\b(?:three|3)\s*times?{_COUNT_SUFFIX}|\btid\b", re.I), "TID"),
    (re.compile(rf"\btwice{_COUNT_SUFFIX}|\b(?:two|2)\s*times?{_COUNT_SUFFIX}|\bbid\b", re.I), "BID"),
    (re.compile(r"\bat (bedtime|night)\b", re.I), "BEDTIME"),
    (re.compile(r"\bwith meals?\b|\bwith food\b", re.I), "WITH_MEALS"),
    (re.compile(rf"\bonce{_COUNT_SUFFIX}|\b(?:one|1)\s*times?{_COUNT_SUFFIX}|\bod\b", re.I), "ONCE_DAILY"),
]


def has_as_needed(raw_text: str) -> bool:
    """True when the text says the medication is taken only when needed.

    Public on purpose. `rx_guardrails`'s G6 guard has to answer "does the
    LABEL say as-needed?" without consulting the pipeline's own
    `frequency_type` -- the measured defect is that the classification
    itself can be wrong, so anything derived from it cannot detect the
    error. See that guard for the full case.
    """
    return bool(_PRN_PATTERN.search(raw_text or ""))


def classify_frequency(raw_text: str) -> str:
    """Tag the semantic frequency category — PRN takes priority over any
    co-occurring day-part wording (e.g. "every 6 hours as needed")."""
    if has_as_needed(raw_text):
        return "PRN"
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(raw_text):
            return category
    return "UNKNOWN"
