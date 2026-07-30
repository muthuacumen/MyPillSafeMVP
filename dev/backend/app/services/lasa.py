"""LASA (Look-Alike Sound-Alike) detection over DIN suggestions.

WHY THIS IS NOT A THRESHOLD (the 2026-07-30 finding)
----------------------------------------------------
`dev/brains/app.py`'s `SEARCH_SCORE_CUTOFF = 75.0` was chosen by a
pre-registered sweep and takes 21 absent-medication queries from 0/21 to
19/21 correctly returning empty. Two negatives survive it, and the ADR
recorded them as pairs "no threshold separates":

    ZOLTIRAX          -> ZOVIRAX                  score  80.0
    TYLENOL PM EXTRA  -> TYLENOL EXTRA STRENGTH   score 100.0

The second number is the point. `token_set_ratio` compares the INTERSECTION
of the two token sets, so a query that is a strict SUPERSET of a product name
scores the maximum possible 100.0 -- the same score an exact match gets.
(The ADR recorded 89.7; measured here it is 100.0, which makes the
"not a threshold" conclusion stronger, not weaker.) No cutoff can separate
these, because there is no gap left to cut in.

What DOES separate them is not how similar the strings are but WHICH WORDS
GOT LOST. Every legitimate near-match keeps all of the label's own words and
merely adds more of its own; every dangerous one drops one:

    METFORMIN         -> SANDOZ METFORMIN FC      label words kept  -> safe
    GRAVOL TABLETS    -> GRAVOL SUPPOSITORIES     label words kept  -> safe
    ZOLTIRAX          -> ZOVIRAX                  lost "ZOLTIRAX"   -> LASA
    TYLENOL PM EXTRA  -> TYLENOL EXTRA STRENGTH   lost "PM"         -> LASA

Measured over the 11,609-DIN profile tier: this catches both documented
survivors (4/4 including each spelling) at a false-fire rate of 1/500 (0.2%)
on exact reference brands and 7/200 (3.5%) on generic-name-only labels, with
ZERO new tunable numbers. See `documentation/evaluation/din_lasa/`.

TWO THINGS THIS DELIBERATELY DOES NOT DO
----------------------------------------
1. It is ONE-DIRECTIONAL. It detects label -> candidate information LOSS, not
   candidate over-specificity: a label reading only "ADVIL" treats "ADVIL
   COLD AND SINUS" as covered, because the label gave no word to lose. That
   direction is handled by the rule that has always governed DIN linking --
   nothing is ever auto-picked, and the user reads the full product name
   before tapping.
2. It NEVER blocks or filters. A near-miss candidate is still shown and still
   linkable; the UI just stops offering it as a one-tap confirm. DIN linking
   is prominently offered and never mandatory (a wrong DIN feeds SB2 a wrong
   appearance row and BB3 a wrong monograph, which is worse than no DIN), so
   suppressing candidates here would trade one silent harm for another.
"""
from __future__ import annotations

import re

from app.services.brains_client import clean_search_query

#: Per-suggestion verdicts, in increasing order of concern.
MATCH_EXACT = "exact"
MATCH_MANUFACTURER = "manufacturer"
MATCH_LOOK_ALIKE = "look_alike"

#: Canadian generic-manufacturer prefixes. A label reading "APO-METFORMIN"
#: against a reference row reading "SANDOZ METFORMIN FC" has lost only the
#: manufacturer, which is a real difference (different DIN, different pill
#: appearance, so SB2 would reject a correct photo) but NOT a wrong-medicine
#: risk. Worth its own, softer verdict rather than the look-alike alarm --
#: firing the alarm on most Canadian generics would train users to dismiss it.
MANUFACTURER_PREFIXES: frozenset[str] = frozenset({
    "APO", "TEVA", "SANDOZ", "PMS", "JAMP", "MINT", "RAN", "AURO", "ACT",
    "MAR", "RIVA", "NAT", "CO", "GD", "PRO", "SEPTA", "SIVEM", "ODAN", "AA",
    "BIO", "VAN", "TARO", "SNS", "NRA", "PHL", "DOM", "NOVO", "GEN",
    "STRIDES", "REDDY", "ZYM", "JUNO", "LUPIN",
})

_TOKEN_SPLIT = re.compile(r"[^A-Z0-9]+")

#: A token that is only digits. Dropped from the coverage requirement: it is
#: a strength or pack size, `brains_client._rerank_by_strength` already ranks
#: on strength, and every candidate shows its strength next to its name -- so
#: a strength difference is VISIBLE to the user, while a lost name word is
#: not. Keeping them would also false-fire whenever the cleaner leaves a bare
#: number behind ("ASPIRIN 81" vs a product spelled "ASPIRIN 81MG").
_DIGITS_ONLY = re.compile(r"^\d+$")

#: Measurement words, dropped for the same reason as digit-only tokens: they
#: describe the strength, not the medicine. Needed because
#: `clean_search_query` deliberately FALLS BACK to the original text when
#: stripping would leave nothing -- so a label name that is only a strength
#: ("500 MG") arrives with its unit intact and would otherwise report every
#: candidate as having lost the word "MG".
#:
#: Note this is an exclusion by MEANING, never by length. Excluding short
#: tokens as a class is the mistake this rule exists to avoid: "PM" and "ES"
#: are two characters and change what is in the pill.
_UNIT_TOKENS: frozenset[str] = frozenset({
    "MG", "MCG", "UG", "G", "KG", "ML", "L", "IU", "U", "UNIT", "UNITS",
    "MEQ", "MMOL", "PCT",
})


def _tokens(value: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split((value or "").upper()) if t]


def label_tokens(label_name: str) -> list[str]:
    """The significant words of a label's medication name.

    Strength and dosage form are stripped with the SAME cleaner the search
    query itself went through (`brains_client.clean_search_query`), so this
    can never demand coverage of a word the search was never given.

    NOTE the minimum token length is 1, not the 3 used by
    `rx_guardrails.value_supported_by_label`. That difference is load-bearing
    and was measured: a >=3 filter silently drops "PM", and "PM" is exactly
    the token that distinguishes TYLENOL PM (which contains diphenhydramine)
    from plain TYLENOL. The short tokens in Canadian OTC naming -- PM, ES,
    XL, SR, XR, CD, DS, HP -- are the ones that change what is in the pill.
    """
    return [
        t for t in _tokens(clean_search_query(label_name))
        if not _DIGITS_ONLY.match(t) and t not in _UNIT_TOKENS
    ]


def missing_label_tokens(label_name: str, product: str) -> list[str]:
    """Words the label printed that this candidate's name does not contain."""
    present = set(_tokens(product))
    return [t for t in label_tokens(label_name) if t not in present]


def classify_name_match(label_name: str, product: str) -> tuple[str, list[str]]:
    """`(verdict, missing_tokens)` for one candidate against one label name."""
    missing = missing_label_tokens(label_name, product)
    if not missing:
        return MATCH_EXACT, []
    if all(token in MANUFACTURER_PREFIXES for token in missing):
        return MATCH_MANUFACTURER, missing
    return MATCH_LOOK_ALIKE, missing


def annotate_suggestions(label_name: str, suggestions: list[dict]) -> list[dict]:
    """Add `name_match` + `missing_tokens` to each suggestion, in place.

    Returns the same list so callers can use it inline. An empty or blank
    label name leaves every suggestion `exact`: with nothing to compare
    against there is no information loss to report, and inventing a warning
    from an absent label would be its own kind of noise.
    """
    if not (label_name or "").strip():
        for suggestion in suggestions:
            suggestion.setdefault("name_match", MATCH_EXACT)
            suggestion.setdefault("missing_tokens", [])
        return suggestions

    for suggestion in suggestions:
        verdict, missing = classify_name_match(label_name, str(suggestion.get("product") or ""))
        suggestion["name_match"] = verdict
        suggestion["missing_tokens"] = missing
    return suggestions


def has_covering_candidate(suggestions: list[dict]) -> bool:
    """True when at least one candidate keeps every word the label printed.

    This is the set-level question the UI acts on. When it is False, EVERY
    option on offer has dropped a word from the label -- the ZOLTIRAX and
    TYLENOL PM state -- and no candidate may be presented as a one-tap
    confirm.
    """
    return any(s.get("name_match") == MATCH_EXACT for s in suggestions)
