"""LASA look-alike detection over DIN suggestions (2026-07-30).

Pure unit tests -- no sidecar, no reference CSV, no HTTP. The candidate names
here are the REAL ones the 11,609-DIN profile tier returns for these queries
(captured by `documentation/evaluation/din_lasa/probe_lasa.py`), so a test
passing here means the rule handles the measured data, not a convenient
fiction.

The two cases that matter most are the pair the ADR recorded as unseparable
by any score cutoff. They are unseparable by score -- ZOLTIRAX->ZOVIRAX
scores 80.0 and TYLENOL PM EXTRA->TYLENOL EXTRA STRENGTH scores the maximum
possible 100.0 -- and that is exactly why the rule here reads lost WORDS
instead.
"""
import pytest

from app.services import lasa


def _suggestion(product: str, **kwargs) -> dict:
    return {"din": "00000001", "product": product, "strength": "500 mg",
            "score": 100.0, "pill_verifiable": True, **kwargs}


# --- the two documented LASA survivors --------------------------------------

def test_zoltirax_against_zovirax_is_a_look_alike():
    verdict, missing = lasa.classify_name_match("ZOLTIRAX 200 MG", "ZOVIRAX")
    assert verdict == lasa.MATCH_LOOK_ALIKE
    assert missing == ["ZOLTIRAX"]


def test_tylenol_pm_against_tylenol_extra_strength_is_a_look_alike():
    """The score is 100.0 here -- the maximum -- because `token_set_ratio`
    compares the token INTERSECTION, so a query that is a superset of the
    product scores as well as an exact match. Nothing about the number can
    catch this; the lost word can."""
    verdict, missing = lasa.classify_name_match(
        "TYLENOL PM EXTRA STRENGTH", "TYLENOL EXTRA STRENGTH"
    )
    assert verdict == lasa.MATCH_LOOK_ALIKE
    assert missing == ["PM"]


def test_the_min_token_length_that_would_blind_the_rule():
    """Regression guard for the measured near-miss in the design itself: the
    >=3-character significance filter that `rx_guardrails` uses would drop
    "PM" and pass this label as an exact match. PM/ES/XL/SR/DS are precisely
    the tokens that change what is in the pill, so `label_tokens` must keep
    2-character words."""
    assert "PM" in lasa.label_tokens("TYLENOL PM EXTRA STRENGTH")


# --- legitimate near-matches must stay one-tap ------------------------------

@pytest.mark.parametrize(("label", "product"), [
    ("METFORMIN 500 MG", "SANDOZ METFORMIN FC"),      # generic -> branded generic
    ("ZOVIRAX 200 MG", "ZOVIRAX"),                    # exact, strength stripped
    ("GRAVOL TABLETS", "GRAVOL SUPPOSITORIES"),       # form differs, name intact
    ("MOTRIN 400 MG", "MOTRIN 200MG"),                # strength differs, visible
    ("ASPIRIN 81 MG", "ASPIRIN REGULAR STRENGTH"),    # reference is more specific
    ("TYLENOL EXTRA STRENGTH", "TYLENOL EXTRA STRENGTH CAPLETS"),
    ("DIGOXIN 0.125 MG", "JAMP DIGOXIN"),
])
def test_legitimate_near_matches_are_not_flagged(label, product):
    verdict, missing = lasa.classify_name_match(label, product)
    assert verdict == lasa.MATCH_EXACT, f"{label!r} -> {product!r} lost {missing}"


def test_a_bare_strength_number_left_by_the_cleaner_does_not_false_fire():
    """"ASPIRIN 81" keeps a digit token the strength regex cannot strip (no
    unit follows it). Digit-only tokens are dropped from the requirement --
    strength is ranked on separately and displayed beside every candidate, so
    a strength difference is visible to the user in a way a lost word is
    not."""
    verdict, _ = lasa.classify_name_match("ASPIRIN 81", "ASPIRIN 81MG")
    assert verdict == lasa.MATCH_EXACT


# --- the softer manufacturer tier -------------------------------------------

def test_manufacturer_only_difference_gets_its_own_verdict():
    """A different manufacturer IS a real difference -- different DIN,
    different pill, so SB2 would reject a correct photo -- but it is not a
    wrong-medicine risk, and firing the look-alike alarm on most Canadian
    generics would train users to dismiss it."""
    verdict, missing = lasa.classify_name_match("APO-METFORMIN 500 MG", "TEVA METFORMIN")
    assert verdict == lasa.MATCH_MANUFACTURER
    assert missing == ["APO"]


def test_manufacturer_plus_a_real_word_is_still_a_look_alike():
    verdict, missing = lasa.classify_name_match("APO-METFORMIN ER 500 MG", "TEVA METFORMIN")
    assert verdict == lasa.MATCH_LOOK_ALIKE
    assert set(missing) == {"APO", "ER"}


# --- the set-level question the UI acts on ----------------------------------

def test_a_set_with_no_covering_candidate_is_the_dangerous_state():
    suggestions = lasa.annotate_suggestions("TYLENOL PM EXTRA", [
        _suggestion("TYLENOL EXTRA STRENGTH"),
        _suggestion("TYLENOL EXTRA STRENGTH CAPLETS"),
    ])
    assert not lasa.has_covering_candidate(suggestions)
    assert all(s["name_match"] == lasa.MATCH_LOOK_ALIKE for s in suggestions)
    assert all(s["missing_tokens"] == ["PM"] for s in suggestions)


def test_one_covering_candidate_is_enough_to_keep_the_panel_normal():
    """A mixed list is the common, healthy case: the exact product plus more
    specific relatives. The near-misses are still labelled, so the UI can
    distinguish ADVIL from ADVIL COLD AND SINUS in the list."""
    suggestions = lasa.annotate_suggestions("ADVIL LIQUI GELS", [
        _suggestion("ADVIL"),
        _suggestion("ADVIL LIQUI GELS"),
    ])
    assert lasa.has_covering_candidate(suggestions)
    assert suggestions[0]["name_match"] == lasa.MATCH_LOOK_ALIKE
    assert suggestions[1]["name_match"] == lasa.MATCH_EXACT


def test_annotation_never_reorders_filters_or_drops_candidates():
    """The rule labels; it does not decide. Anything else would make DIN
    linking blocking, which is explicitly rejected."""
    original = [_suggestion("ZOVIRAX", din="00636622"),
                _suggestion("ZOVIRAX CREAM", din="00636630")]
    annotated = lasa.annotate_suggestions("ZOLTIRAX", original)
    assert annotated is original
    assert [s["din"] for s in annotated] == ["00636622", "00636630"]


# --- degenerate input -------------------------------------------------------

@pytest.mark.parametrize("label", ["", "   ", None])
def test_a_blank_label_name_warns_about_nothing(label):
    """With no label to compare against there is no information loss to
    report, and a warning invented from an absent label is its own noise."""
    suggestions = lasa.annotate_suggestions(label, [_suggestion("ZOVIRAX")])
    assert suggestions[0]["name_match"] == lasa.MATCH_EXACT
    assert suggestions[0]["missing_tokens"] == []


def test_a_label_that_is_only_a_strength_does_not_flag_everything():
    """`clean_search_query` falls back to the original text when stripping
    would empty it, so "500 MG" survives as the query -- and its only token
    is digits, which the rule ignores."""
    suggestions = lasa.annotate_suggestions("500 MG", [_suggestion("METFORMIN")])
    assert suggestions[0]["name_match"] == lasa.MATCH_EXACT


def test_an_empty_suggestion_list_is_handled():
    assert lasa.annotate_suggestions("ZOLTIRAX", []) == []
    assert not lasa.has_covering_candidate([])
