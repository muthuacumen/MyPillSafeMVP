"""FixbyOPUS3 Task A2/A5 -- the deterministic guardrails, one test class per
guard, plus the derivation property that makes the measured H7 failure class
impossible by construction.

These are pure unit tests: no DB, no HTTP, no model. That is the point --
the guards are the part of this system that must be true regardless of which
proposer spoke or whether anything was reachable.
"""
import pytest

from app.services import rx_guardrails as g
from app.services.prescription_parser import parse_medications


def _llm(**kwargs) -> g.MedicationProposal:
    base = {
        "drug_name": "AMLODIPINE 5 MG",
        "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY",
        "explicit_times": [],
        "with_food": False,
    }
    return g.from_llm_medication({**base, **kwargs})


# --- OCR-confusable normalization (the fold G2 compares over) ---------------

@pytest.mark.parametrize(
    ("noisy", "clean"),
    [
        ("AT0RVASTATIN", "atorvastatin"),
        ("2O MG", "20mg"),
        ("Refi11s", "refills"),
        ("0ty: 9O", "qty: 90".replace("q", "0")),  # 0ty vs Oty -- both fold to the same
        ("B8", "BB"),
        ("modern", "modem"),  # rn <-> m, the classic ligature confusion
    ],
)
def test_confusable_fold_collapses_ocr_lookalikes(noisy, clean):
    assert g.normalize_confusable(noisy) == g.normalize_confusable(clean)


def test_confusable_fold_does_not_collapse_genuinely_different_drugs():
    assert g.normalize_confusable("metformin") != g.normalize_confusable("metoprolol")
    assert g.normalize_confusable("lantus") != g.normalize_confusable("lasix")


# --- G1 catalog -------------------------------------------------------------

def test_g1_flags_when_reference_has_no_hit_but_keeps_the_medication():
    med = _llm()
    g.flag_not_in_reference(med, [])
    assert g.FLAG_NOT_IN_REFERENCE in med.flags
    assert med.drug_name == "AMLODIPINE 5 MG"  # still shown -- reference is incomplete


def test_g1_silent_when_the_reference_matched():
    med = _llm()
    g.flag_not_in_reference(med, [{"din": "00123456", "product": "AMLODIPINE", "strength": "5 MG", "score": 95.0}])
    assert g.FLAG_NOT_IN_REFERENCE not in med.flags


# --- G2 no-invention, ASYMMETRIC (spec §4, amended 2026-07-28) --------------

H10_NOISY_LABEL = (
    "C0STCO PHARMACY\n"
    "AT0RVASTATIN 2O MG TABLET\n"
    "TAKE 1 TABLET AT BEDTlME\n"
    "0ty: 9O Refi11s: 2\n"
)


def test_g2_keeps_name_and_dosage_on_an_ocr_noise_label():
    """The amendment's whole reason to exist. A stripping guard would have
    deleted the CORRECT `atorvastatin` / `20mg` off the held-out
    H10-ocr-noise case -- destroying value on exactly the noisy labels the
    LLM proposer was selected to rescue, and leaving a senior a blank field
    to retype from a label they may not read well."""
    med = _llm(drug_name="ATORVASTATIN 20 MG TABLET", dosage="20 mg", frequency_type="BEDTIME")
    [out] = g.apply([med], H10_NOISY_LABEL)
    assert out.drug_name == "ATORVASTATIN 20 MG TABLET"
    assert out.dosage == "20 mg"
    assert out.specific_times == ["21:00"]
    assert out.flags == []  # the fold matched -- no spurious flag either


def test_g2_keeps_but_flags_an_invented_dosage_and_that_flag_blocks_approval():
    med = _llm(drug_name="ATORVASTATIN", dosage="80 mg", frequency_type="BEDTIME")
    [out] = g.apply([med], H10_NOISY_LABEL)
    assert out.dosage == "80 mg", "G2 must KEEP the value, never null it"
    assert g.FLAG_NOT_ON_LABEL in out.flags
    assert g.unresolved_blocking_flags(
        out.flags, specific_times=out.specific_times, confirmed_flags=None
    ) == [g.FLAG_NOT_ON_LABEL]
    # ...and the user explicitly confirming that field clears the block.
    assert g.unresolved_blocking_flags(
        out.flags, specific_times=out.specific_times, confirmed_flags=[g.FLAG_NOT_ON_LABEL]
    ) == []


def test_g2_flags_a_wholly_invented_drug_name():
    med = _llm(drug_name="LISINOPRIL", dosage=None, frequency_type="ONCE_DAILY")
    [out] = g.apply([med], H10_NOISY_LABEL)
    assert out.drug_name == "LISINOPRIL"
    assert g.FLAG_NOT_ON_LABEL in out.flags


def test_g2_strips_a_time_that_is_not_printed_on_the_label():
    """Times are the asymmetric half: they STRIP, because a wrong reminder
    time fires a wrong reminder and G4 supplies a correct one anyway."""
    med = _llm(drug_name="METFORMIN 500 MG", dosage="500 mg",
               frequency_type="BID", explicit_times=["07:30", "19:30"])
    [out] = g.apply([med], "METFORMIN 500 MG\nTAKE 1 TABLET TWICE DAILY\n")
    assert out.explicit_times == []
    assert g.FLAG_NOT_ON_LABEL in out.flags
    assert out.specific_times == ["08:00", "18:00"]  # G4 re-supplied them


def test_g2_keeps_a_time_that_is_printed_on_the_label():
    med = _llm(drug_name="METFORMIN 500 MG", dosage="500 mg",
               frequency_type="BID", explicit_times=["08:00", "20:00"])
    [out] = g.apply([med], "METFORMIN 500 MG\nTake 1 tablet at 8:00 AM and 8:00 PM\n")
    assert out.specific_times == ["08:00", "20:00"]
    assert g.FLAG_NOT_ON_LABEL not in out.flags


# --- G3 schema --------------------------------------------------------------

def test_g3_coerces_an_out_of_enum_frequency_to_unknown():
    med = _llm(frequency_type="EVERY_OTHER_TUESDAY")
    [out] = g.apply([med], "AMLODIPINE 5 MG\n")
    assert out.frequency_type == "UNKNOWN"
    assert g.FLAG_NEEDS_SCHEDULE in out.flags


def test_g3_drops_malformed_clock_times():
    med = _llm(frequency_type="BID", explicit_times=["8am", "25:00", "18:00", ""])
    [out] = g.apply([med], "METFORMIN 500 MG at 18:00 twice daily\n")
    assert out.explicit_times == ["18:00"]


# --- G4 no-silent-defaults + deterministic derivation -----------------------

@pytest.mark.parametrize(
    ("frequency", "expected"),
    [
        ("ONCE_DAILY", ["08:00"]),
        ("BID", ["08:00", "18:00"]),
        ("TID", ["08:00", "13:00", "18:00"]),
        ("QID", ["08:00", "13:00", "18:00", "21:00"]),
        ("BEDTIME", ["21:00"]),
        ("WITH_MEALS", ["08:00", "13:00", "18:00"]),
    ],
)
def test_g4_derives_the_canonical_times(frequency, expected):
    med = _llm(frequency_type=frequency)
    [out] = g.apply([med], "AMLODIPINE 5 MG\n")
    assert out.specific_times == expected


@pytest.mark.parametrize("frequency", ["PRN", "WEEKLY", "EVERY_N_HOURS", "TAPER", "UNKNOWN"])
def test_g4_never_invents_a_time_for_an_unschedulable_frequency(frequency):
    """The catastrophic event this whole redesign exists to prevent: a
    once-weekly bisphosphonate acquiring a daily 08:00 reminder. Measured on
    the regex parser 2026-07-28 as a real safety event."""
    med = _llm(frequency_type=frequency)
    [out] = g.apply([med], "APO-ALENDRONATE 70 MG TABLET\nTAKE 1 TABLET ONCE WEEKLY\n")
    assert out.specific_times == []
    assert g.FLAG_NEEDS_SCHEDULE in out.flags


def test_g4_makes_the_h7_failure_class_impossible_by_construction():
    """H7 (Jean Coutu, French, "2 FOIS PAR JOUR") was qwen2.5:7b's ONLY
    held-out miss on 2026-07-28: it emitted 08:00 + 13:00 for a BID label.
    The model is no longer asked, so no model output can produce that
    outcome -- BID is 08:00 + 18:00 or the table is wrong."""
    french_label = (
        "Jean Coutu Pharmacie\n"
        "LOSARTAN 50 MG COMPRIME\n"
        "PRENDRE 1 COMPRIME 2 FOIS PAR JOUR AVEC DE LA NOURRITURE\n"
    )
    # Even if the proposer hands us the exact wrong times it produced then,
    # they are not on the label, so G2 strips them and G4 re-derives.
    med = _llm(drug_name="LOSARTAN 50 MG COMPRIME", dosage="50 mg",
               frequency_type="BID", explicit_times=["08:00", "13:00"])
    [out] = g.apply([med], french_label)
    assert out.specific_times == ["08:00", "18:00"]


def test_g4_strips_the_regex_parsers_silent_default_morning():
    """The regex parser hands back time_slots=['morning'] / ['08:00'] for
    text it did not understand at all (see `timing_parser.parse_frequency`).
    On the guarded path that default must not survive -- an unparsed label
    gets `needs_schedule` and NO time (non-negotiable §0.3)."""
    raw = "SOME UNREADABLE LABEL TEXT WITH NO TIMING WORDS AT ALL\n"
    [parsed] = parse_medications(raw)
    assert parsed.specific_times == ["08:00"], "precondition: the regex parser still defaults"
    [out] = g.apply([g.from_parsed_medication(parsed)], raw)
    assert out.frequency_type == "UNKNOWN"
    assert out.specific_times == []
    assert g.FLAG_NEEDS_SCHEDULE in out.flags


def test_needs_schedule_is_resolved_by_actually_setting_a_time():
    assert g.unresolved_blocking_flags(
        [g.FLAG_NEEDS_SCHEDULE], specific_times=[], confirmed_flags=None
    ) == [g.FLAG_NEEDS_SCHEDULE]
    assert g.unresolved_blocking_flags(
        [g.FLAG_NEEDS_SCHEDULE], specific_times=["09:00"], confirmed_flags=None
    ) == []
    # ...or by the user explicitly choosing "as needed, no fixed time".
    assert g.unresolved_blocking_flags(
        [g.FLAG_NEEDS_SCHEDULE], specific_times=[], confirmed_flags=[g.FLAG_NEEDS_SCHEDULE]
    ) == []


def test_informational_flags_never_block_approval():
    assert g.unresolved_blocking_flags(
        [g.FLAG_NOT_IN_REFERENCE, g.FLAG_CONFLICT],
        specific_times=["08:00"], confirmed_flags=None,
    ) == []


# --- G5 conflict ------------------------------------------------------------

def test_g5_flags_duplicate_drug_names():
    raw = "METFORMIN 500 MG\nTAKE 1 TABLET TWICE DAILY\nMETFORMIN 500 MG\nTAKE 1 TABLET AT BEDTIME\n"
    meds = [
        _llm(drug_name="METFORMIN 500 MG", dosage="500 mg", frequency_type="BID"),
        _llm(drug_name="METFORMIN 500 MG", dosage="500 mg", frequency_type="BEDTIME"),
    ]
    out = g.apply(meds, raw)
    assert all(g.FLAG_CONFLICT in med.flags for med in out)
    # Both are still shown -- the user resolves it, the app does not guess.
    assert len(out) == 2


def test_g5_flags_a_dosage_that_contradicts_the_strength_in_its_own_name():
    raw = "METFORMIN 500 MG\nTAKE 1 TABLET TWICE DAILY\n"
    med = _llm(drug_name="METFORMIN 500 MG", dosage="850 mg", frequency_type="BID")
    [out] = g.apply([med], raw)
    assert g.FLAG_CONFLICT in out.flags


def test_g5_quiet_on_a_consistent_single_medication():
    raw = "METFORMIN 500 MG\nTAKE 1 TABLET TWICE DAILY\n"
    med = _llm(drug_name="METFORMIN 500 MG", dosage="500 mg", frequency_type="BID")
    [out] = g.apply([med], raw)
    assert g.FLAG_CONFLICT not in out.flags


# --- proposer-agnosticism ---------------------------------------------------

def test_both_proposers_land_on_identical_guarded_output_for_the_same_label():
    """The architectural claim, tested: swapping the proposer changes who
    proposed, not what the safety layer did."""
    raw = "APO-ALENDRONATE 70 MG TABLET\nTAKE 1 TABLET ONCE WEEKLY\n"
    from_regex = g.apply([g.from_parsed_medication(m) for m in parse_medications(raw)], raw)
    from_llm = g.apply(
        [_llm(drug_name="APO-ALENDRONATE 70 MG TABLET", dosage="70 mg", frequency_type="WEEKLY")],
        raw,
    )
    assert from_regex[0].specific_times == from_llm[0].specific_times == []
    assert g.FLAG_NEEDS_SCHEDULE in from_regex[0].flags
    assert g.FLAG_NEEDS_SCHEDULE in from_llm[0].flags


# --- G6 as-needed truth check (2026-07-30) ----------------------------------
#
# THE regression set for the measured label-C defect.
#
# WHY THESE TESTS INJECT `BEDTIME` BY HAND. The shipped qwen proposer emits
# that classification only INTERMITTENTLY -- measured 2026-07-30, it answered
# BEDTIME on three consecutive calls and PRN on three more forty minutes
# later, each burst internally unanimous. An end-to-end run therefore cannot
# be relied on to reproduce the failing input at all, which is exactly why
# the guard has to exist and why its proof lives here instead: every case
# below hands the guards the wrong classification deliberately. Testing with
# `frequency_type="PRN"` would test nothing, because the entire premise is
# that the classification cannot be trusted.

#: Label C of the published eval set, verbatim
#: (documentation/evaluation/rx_parsing/labels_and_ground_truth.json).
_LABEL_C = (
    "Shoppers Drug Mart\n"
    "123 King St W, Kitchener ON\n"
    "APO-METFORMIN 500 MG\n"
    "Take 1 tablet twice daily with food\n"
    "TEVA-NAPROXEN 500 MG\n"
    "Take 1 tablet at bedtime as needed for pain\n"
    "DIN: 02353377\n"
)


def test_g6_label_c_as_needed_nsaid_gets_no_fixed_reminder():
    """The defect, end to end: an as-needed NSAID must not acquire 21:00."""
    meds = g.apply(
        [
            _llm(drug_name="APO-METFORMIN 500 MG", dosage="500 mg", frequency_type="BID"),
            _llm(drug_name="TEVA-NAPROXEN 500 MG", dosage="500 mg", frequency_type="BEDTIME"),
        ],
        _LABEL_C,
    )
    metformin, naproxen = meds

    assert naproxen.specific_times == [], "an as-needed NSAID must carry no reminder time"
    assert naproxen.as_needed is True
    assert g.FLAG_AS_NEEDED in naproxen.flags
    assert g.FLAG_NEEDS_SCHEDULE in naproxen.flags
    # The day-part the label DID print stays visible -- G6 withholds the
    # reminder, it does not rewrite the label.
    assert naproxen.frequency_type == "BEDTIME"


def test_g6_does_not_leak_as_needed_onto_the_other_medication_on_the_label():
    """The scoping half, and the more dangerous failure to get wrong: trading
    an invented reminder for a LOST one on the scheduled medication."""
    meds = g.apply(
        [
            _llm(drug_name="APO-METFORMIN 500 MG", dosage="500 mg", frequency_type="BID"),
            _llm(drug_name="TEVA-NAPROXEN 500 MG", dosage="500 mg", frequency_type="BEDTIME"),
        ],
        _LABEL_C,
    )
    metformin = meds[0]
    assert metformin.specific_times == ["08:00", "18:00"]
    assert metformin.as_needed is False
    assert g.FLAG_AS_NEEDED not in metformin.flags
    assert g.FLAG_NEEDS_SCHEDULE not in metformin.flags


def test_g6_windows_are_bounded_by_the_next_located_medication():
    """Directly asserts the windowing, so a refactor that widens a window
    fails here rather than silently in the flags."""
    meds = [
        _llm(drug_name="APO-METFORMIN 500 MG"),
        _llm(drug_name="TEVA-NAPROXEN 500 MG"),
    ]
    first, second = g.as_needed_windows(meds, _LABEL_C)
    assert "as needed" not in first
    assert "twice daily" in first
    assert "as needed" in second


def test_g6_single_medication_reads_the_whole_label():
    """One medication has nothing to disambiguate, and its instruction line
    is not guaranteed to follow its name -- so the window is the whole text
    even when the name never matches a line."""
    raw = (
        "CONESTOGA PHARMACY\n"
        "Take 1 tablet every 6 hours as needed for pain\n"
        "ACETAMINOPHEN 500 MG\n"
    )
    [out] = g.apply([_llm(drug_name="ACETAMINOPHEN 500 MG", frequency_type="EVERY_N_HOURS")], raw)
    assert out.as_needed is True
    assert out.specific_times == []


def test_g6_falls_back_to_the_whole_label_when_a_name_cannot_be_located():
    """Conservative direction: an unlocatable name must not narrow the search
    for the phrase. Over-attribution withholds a reminder and asks the user;
    under-attribution invents one."""
    raw = (
        "IBUPROFEN 400 MG\n"
        "Take 1 tablet three times daily\n"
        "SOMETHING THE OCR MANGLED\n"
        "Take 1 tablet as needed\n"
    )
    meds = g.apply(
        [
            _llm(drug_name="IBUPROFEN 400 MG", frequency_type="TID"),
            _llm(drug_name="ZZ UNMATCHABLE NAME", frequency_type="ONCE_DAILY"),
        ],
        raw,
    )
    assert meds[1].as_needed is True
    assert meds[1].specific_times == []


def test_g6_suppresses_even_a_clock_time_printed_on_an_as_needed_label():
    """On an as-needed medication a printed time is a ceiling, not a
    schedule -- so it must not become a reminder either."""
    raw = "TRAMADOL 50 MG\nTake 1 tablet at 8:00 PM as needed for pain\n"
    [out] = g.apply(
        [_llm(drug_name="TRAMADOL 50 MG", frequency_type="PRN", explicit_times=["20:00"])],
        raw,
    )
    assert out.specific_times == []
    assert g.FLAG_NEEDS_SCHEDULE in out.flags


def test_g6_quiet_on_a_label_that_never_says_as_needed():
    raw = "RAMIPRIL 5 MG\nTake 1 capsule once daily in the morning\n"
    [out] = g.apply([_llm(drug_name="RAMIPRIL 5 MG", frequency_type="ONCE_DAILY")], raw)
    assert out.as_needed is False
    assert g.FLAG_AS_NEEDED not in out.flags
    assert out.specific_times == ["08:00"]


def test_g6_gives_the_regex_proposer_the_same_explanatory_flag():
    """The regex path already returned PRN with no times, but said nothing
    about WHY there were none. Both proposers now explain themselves
    identically."""
    raw = "TEVA-NAPROXEN 500 MG\nTake 1 tablet at bedtime as needed for pain\n"
    from_regex = g.apply([g.from_parsed_medication(m) for m in parse_medications(raw)], raw)
    from_llm = g.apply([_llm(drug_name="TEVA-NAPROXEN 500 MG", frequency_type="BEDTIME")], raw)
    assert from_regex[0].specific_times == from_llm[0].specific_times == []
    assert g.FLAG_AS_NEEDED in from_regex[0].flags
    assert g.FLAG_AS_NEEDED in from_llm[0].flags
