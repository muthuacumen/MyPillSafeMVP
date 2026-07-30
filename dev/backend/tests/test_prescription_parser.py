"""Unit tests for the multi-medication OCR text parser (no DB/HTTP)."""
from app.services.prescription_parser import (
    _DOSAGE,
    _parse_block,
    parse_medications,
)

_DEMO_LETTER = """\
CONESTOGA MEDICAL CENTRE
123 University Avenue West, Waterloo, ON N2L 3G1 | Tel: (519) 888-4567 | Fax: (519) 888-4568
FOR DEMONSTRATION PURPOSES ONLY  PILLSAFE CAPSTONE PROJECT
PATIENT NAME
DATE OF BIRTH
DATE
HEALTH CARD
Sumanth Reddy K
May 15, 1990
June 24, 2026
4821-567-890 ON
RX 1
Acetaminophen 500mg (Tylenol Extra Strength).
Take 2 tablets every 6 hours as needed for pain or fever - do not exceed 8 tablets in 24 hours
Qty: 100 tablets
Refills: 2
DIN: 00559407
RX 2
Ibuprofen 200mg (Advil)
Take 1-2 tablets THREE TIMES DAILY with meals (morning, noon and night) for joint pain - take with food
Qty: 90 tablets
Refills: 1
DIN: 00587915
RX 3
Loratadine 10mg (Claritin).
Take 1 tablet ONCE DAILY in the morning for seasonal allergies.
Qty: 30 tablets
Refills: 3
DIN: 00782696
Prescriber: Dr. Anasuya Bhima, MD.
CPSO#: 234567 | DEA: AB1234567
Conestoga Medical Centre, Waterloo ON
Signature / Authorized Prescriber.
"""


def test_parses_three_distinct_medications():
    meds = parse_medications(_DEMO_LETTER)
    assert len(meds) == 3
    names = [m.drug_name for m in meds]
    assert names == ["Acetaminophen", "Ibuprofen", "Loratadine"]


def test_clinic_letterhead_is_never_a_drug_name():
    meds = parse_medications(_DEMO_LETTER)
    assert all("CONESTOGA" not in m.drug_name.upper() for m in meds)


def test_dosage_extracted_per_medication():
    meds = parse_medications(_DEMO_LETTER)
    dosages = {m.drug_name: m.dosage for m in meds}
    assert dosages["Acetaminophen"] == "500mg"
    assert dosages["Ibuprofen"] == "200mg"
    assert dosages["Loratadine"] == "10mg"


def test_ibuprofen_schedule_does_not_bleed_into_loratadine():
    meds = parse_medications(_DEMO_LETTER)
    loratadine = next(m for m in meds if m.drug_name == "Loratadine")
    assert loratadine.time_slots == ["morning"]
    assert loratadine.frequency_type == "ONCE_DAILY"


def test_ibuprofen_is_tid_with_food():
    meds = parse_medications(_DEMO_LETTER)
    ibuprofen = next(m for m in meds if m.drug_name == "Ibuprofen")
    assert ibuprofen.frequency_type == "TID"
    assert ibuprofen.time_slots == ["morning", "afternoon", "evening"]
    assert ibuprofen.specific_times == ["08:00", "13:00", "18:00"]
    assert ibuprofen.with_food is True
    assert ibuprofen.purpose == "joint pain"


def test_acetaminophen_is_prn_with_max_daily_dose_and_no_fixed_times():
    meds = parse_medications(_DEMO_LETTER)
    acetaminophen = next(m for m in meds if m.drug_name == "Acetaminophen")
    assert acetaminophen.frequency_type == "PRN"
    assert acetaminophen.max_daily_dose == 8
    assert acetaminophen.time_slots == []
    assert acetaminophen.specific_times == []
    assert acetaminophen.purpose == "pain or fever"


def test_no_rx_markers_falls_back_to_single_medication():
    meds = parse_medications("Metformin HCl 500mg — twice daily with meals. Dr. A. Chen. Refills: 2.")
    assert len(meds) == 1
    assert "Metformin" in meds[0].drug_name
    assert meds[0].time_slots == ["morning", "evening"]


def test_empty_text_returns_single_unknown_fallback():
    meds = parse_medications("")
    assert len(meds) == 1
    assert meds[0].drug_name == "Unknown medication"


# --- FixbySonnet1 Task 1 (Bug #1): real pharmacy labels never carry "RX n"
# markers, so they always hit the no-marker fallback. These regression
# tests cover the fallback hardening: drug_name must never be the
# pharmacy/clinic header, and frequency_text must never be the raw OCR
# dump (which is how a real label crashed the DB INSERT -- String(255)).

_REALISTIC_LABEL = """\
CONESTOGA PHARMACY
123 University Avenue West, Waterloo, ON N2L 3G1
Tel: (519) 888-4567 | Fax: (519) 888-4568
www.conestogapharmacy.ca
Sumanth Reddy K
DOB: May 15, 1990
Acetaminophen 500mg Tablets
Take 2 tablets every 6 hours as needed for pain or fever.
Do not exceed 8 tablets in 24 hours.
Qty: 100  Refills: 2
DIN: 00559407
Pharmacist: J. Smith
"""


def test_real_label_drug_name_is_never_the_pharmacy_header():
    meds = parse_medications(_REALISTIC_LABEL)
    assert len(meds) == 1
    assert "PHARMACY" not in meds[0].drug_name.upper()
    assert "CONESTOGA" not in meds[0].drug_name.upper()
    assert "Acetaminophen" in meds[0].drug_name


def test_real_label_frequency_text_excludes_header_and_footer_noise():
    meds = parse_medications(_REALISTIC_LABEL)
    freq = meds[0].frequency_text
    assert "PHARMACY" not in freq.upper()
    assert "Tel:" not in freq
    assert "DIN:" not in freq
    assert "every 6 hours" in freq.lower()
    assert len(freq) <= 255


# Synthetic multi-OTC-med label shape -- transcribed verbatim (layout, not
# pixels) from archive/docs/Synthetic_Prescription_Test1.png (a sibling of
# this repo at D:\Projects\PillSafe\archive\docs\, outside the git checkout
# -- see Builder Report). Real shape: a plain "Rx" heading followed by a
# NUMBERED list ("1.  2. ...") with indented "Sig:" lines -- NOT "RX n"
# markers -- so this hits the same no-marker fallback as any other real
# label. Five OTC meds is also what stress-tests the length clamp for real:
# five "Sig:" lines is comfortably over 255 chars combined.
_SYNTHETIC_OTC_LABEL = """\
Conestoga Family Health Clinic
123 Health Street, Kitchener, ON  N2G 1A1
Tel: (519) 555-0134    Fax: (519) 555-0135
Patient: Muthuraj Jayakumar
DOB: 1990-01-01
Prescriber: Dr. A. Reyes, MD
Date: 2026-07-27
Patient ID: 004821
Lic. #: ON-88213
Rx
1. Tylenol Extra Strength (Acetaminophen 500 mg)
Sig: Take 1-2 tablets by mouth every 6 hours as needed for pain. Qty: 30  Refills: 1
2. Advil (Ibuprofen 200 mg)
Sig: Take 1 tablet by mouth every 4-6 hours with food. Qty: 24  Refills: 0
3. Benadryl Allergy (Diphenhydramine HCl 25 mg)
Sig: Take 1 tablet by mouth at bedtime for allergy symptoms. Qty: 20  Refills: 0
4. Pepcid Maximum Strength (Famotidine 20 mg)
Sig: Take 1 tablet by mouth once daily before breakfast. Qty: 30  Refills: 2
5. Allergy Remedy (Loratadine 10 mg)
Sig: Take 1 tablet by mouth once daily. Qty: 30  Refills: 2
Notes: Patient counselled on OTC interactions. Take with food if GI upset occurs.
Dr. A. Reyes
Signature            License #: ON-88213
"""


def test_synthetic_otc_label_splits_into_five_medications():
    """No "RX n" markers in the real doc (numbered list + Sig: lines
    instead), so it takes the no-marker fallback like every real pharmacy
    label.

    This assertion CHANGED: it previously required exactly one record and
    documented multi-medication splitting as out of scope, which meant four
    of the five prescribed medications were silently dropped on a real
    multi-drug label. The enumeration splitter now returns one record per
    listed medication; the clamp/no-crash guarantees below are unchanged
    and still apply per record."""
    meds = parse_medications(_SYNTHETIC_OTC_LABEL)
    assert len(meds) == 5
    names = " | ".join(m.drug_name for m in meds).lower()
    for expected in ("tylenol", "advil", "benadryl", "pepcid", "allergy remedy"):
        assert expected in names, f"{expected!r} missing from {names!r}"
    for med in meds:
        # The clinic letterhead precedes the first list item, so no record
        # may be named after it, and the enumeration marker must be gone.
        assert "CLINIC" not in med.drug_name.upper()
        assert not med.drug_name[:3].strip().startswith(("1.", "2.", "3.", "4.", "5."))
        assert len(med.drug_name) <= 255
        assert len(med.frequency_text) <= 255
        assert len(med.frequency_type) <= 30
    # The five Sig: lines combined are well over 255 chars -- this is the
    # exact shape that crashed the deploy (StringDataRightTruncationError).
    combined_sig_length = sum(len(ln) for ln in _SYNTHETIC_OTC_LABEL.splitlines() if ln.startswith('Sig:'))
    assert combined_sig_length > 255


def test_synthetic_otc_label_schedules_are_per_medication():
    """Each split record carries its OWN schedule -- the bedtime antihistamine
    must not inherit the once-daily antacid's morning slot, and the
    as-needed painkiller must carry no fixed dose time at all."""
    meds = {m.drug_name.lower(): m for m in parse_medications(_SYNTHETIC_OTC_LABEL)}

    tylenol = next(m for k, m in meds.items() if "tylenol" in k)
    assert tylenol.frequency_type == "PRN"
    assert tylenol.time_slots == [] and tylenol.specific_times == []
    assert tylenol.dosage == "500mg"

    benadryl = next(m for k, m in meds.items() if "benadryl" in k)
    assert benadryl.frequency_type == "BEDTIME"
    assert benadryl.specific_times == ["21:00"]

    pepcid = next(m for k, m in meds.items() if "pepcid" in k)
    assert pepcid.frequency_type == "ONCE_DAILY"
    assert pepcid.specific_times == ["08:00"]


def test_garbled_realistic_label_over_1000_chars_never_overflows_columns():
    """Regression for the deploy crash: a real label's raw OCR text (garbled,
    no RX markers) must never blow past DB column limits regardless of shape."""
    noise_line = "SPOT HOSPITAL PHARMACY DIVISION RECEIPT CODE 998877 " * 20
    garbled = (noise_line + "\n") * 3 + (
        "Amoxicillin 500mg Capsules\n"
        "Take 1 capsule three times daily with food for infection - do not exceed 21 capsules\n"
    ) + (noise_line + "\n") * 10
    assert len(garbled) > 1000
    meds = parse_medications(garbled)
    assert len(meds) == 1
    assert len(meds[0].drug_name) <= 255
    assert len(meds[0].frequency_text) <= 255
    assert len(meds[0].frequency_type) <= 30
    assert (meds[0].purpose or "") == "" or len(meds[0].purpose) <= 100


# --- FixbySonnet2 (defects A/B/C): the RX-marker path (_parse_block) was
# already correct -- it truncates at the dosage match, not on a hyphen --
# these regression tests target only the no-marker fallback, which is where
# all three defects lived. Each of the three defect tests below was checked
# to FAIL against the pre-fix code and PASS after (see Builder Report).

def test_apo_metformin_survives_hyphen_and_beats_pharmacy_header():
    """Defect A (headline bug): a bare-hyphen split truncated
    "APO-METFORMIN 500 MG" to "APO", destroying the dosage signal
    _select_drug_name depends on -- which let the pharmacy header line win
    the candidacy instead."""
    label = "Shoppers Drug Mart\n123 King St W\nAPO-METFORMIN 500 MG\nTake 1 tablet twice daily"
    meds = parse_medications(label)
    assert meds[0].drug_name == "APO-METFORMIN 500 MG"


def test_canadian_generic_prefixes_survive_hyphen_split():
    """Defect A, more prefixes: the dominant Canadian generic naming
    convention is MANUFACTURER-DRUGNAME. A bare hyphen split truncates
    every one of these to the manufacturer prefix alone."""
    prefixed_names = [
        "PMS-AMLODIPINE 5 MG",
        "TEVA-NAPROXEN 500 MG",
        "NOVO-TRAZODONE 50 MG",
        "CO-TRIMOXAZOLE 800 MG",
    ]
    for name in prefixed_names:
        label = f"Rexall Pharmacy\n456 Main St\n{name}\nTake 1 tablet once daily"
        meds = parse_medications(label)
        assert meds[0].drug_name == name, f"{name!r} was mangled to {meds[0].drug_name!r}"


def test_telmisartan_and_montelukast_not_rejected_as_header_noise():
    """Defect B: an un-bounded 'tel' substring inside _HEADER_NOISE rejected
    any drug name merely CONTAINING "tel" as pharmacy/clinic header noise --
    TELmisartan and monTELukast, both top-50 Canadian prescriptions."""
    meds_tel = parse_medications(
        "Some Clinic\nTELMISARTAN 40 MG\nTake 1 tablet once daily in the morning"
    )
    assert meds_tel[0].drug_name == "TELMISARTAN 40 MG"

    meds_mon = parse_medications(
        "Some Clinic\nMONTELUKAST 10 MG\nTake 1 tablet once daily in the evening"
    )
    assert meds_mon[0].drug_name == "MONTELUKAST 10 MG"


def test_explicit_clock_times_both_recovered_and_shown():
    """Defect C: explicit clock times were absent from _INSTRUCTION_SIGNAL,
    so the filtered text handed to timing_parser was empty and only the
    default-morning fallback (['08:00']) survived -- the 8 PM dose was
    silently lost. Both doses must now be recovered, and the clock-time
    line must still appear in the stored/displayed frequency_text."""
    meds = parse_medications("ATORVASTATIN 20 MG\nTake 1 tablet at 8:00 AM and 8:00 PM")
    assert meds[0].specific_times == ["08:00", "20:00"]
    assert "8:00 AM" in meds[0].frequency_text
    assert "8:00 PM" in meds[0].frequency_text


def test_parse_block_rx_marker_path_keeps_apo_metformin_intact():
    """Proof the RX-marker path was not touched by the Defect A fix: it
    already truncates at the dosage match (not on a hyphen), so
    APO-METFORMIN was never broken there and must not regress now."""
    med = _parse_block("APO-METFORMIN 500 MG\nTake 1 tablet twice daily")
    assert med.drug_name == "APO-METFORMIN"
    assert med.dosage == "500MG"


def test_clamp_lock_garbled_dump_over_10kb_stays_within_limits_both_paths():
    """Clamp lock (must not regress): _LIMITS / _clamp /
    ParsedMedication.__post_init__ are load-bearing -- they make
    StringDataRightTruncationError structurally impossible regardless of
    parse path or input size. Exercises both the no-marker fallback and the
    RX-marker path against the same oversized, garbled input."""
    noise_line = "SPOT HOSPITAL PHARMACY DIVISION RECEIPT CODE 998877 " * 60
    garbled = (noise_line + "\n") * 4 + (
        "APO-METFORMIN 500 MG\n"
        "Take 1 tablet twice daily with food for diabetes at 8:00 AM and "
        "8:00 PM - do not exceed 4 tablets\n"
    ) + (noise_line + "\n") * 4
    assert len(garbled) > 10_000

    def _assert_bounded(med):
        assert len(med.drug_name) <= 255
        assert len(med.frequency_text) <= 255
        assert len(med.frequency_type) <= 30
        assert (med.dosage or "") == "" or len(med.dosage) <= 100
        assert (med.purpose or "") == "" or len(med.purpose) <= 100

    # no-marker fallback path
    meds = parse_medications(garbled)
    assert len(meds) == 1
    _assert_bounded(meds[0])

    # RX n marker path, same oversized garbled content per block
    meds_rx = parse_medications("RX 1\n" + garbled)
    assert len(meds_rx) == 1
    _assert_bounded(meds_rx[0])


# --- Multi-medication splitting of a no-marker label. A missed split loses
# a prescribed medication; a PHANTOM split invents one the patient was never
# given and schedules reminders for it. The trap tests below are the more
# important half of this group.

def test_unenumerated_stacked_medications_split_on_dosage_lines():
    """No list markers at all -- two name+directions blocks stacked. The
    dosage-line fallback must recover both, not just the first."""
    label = (
        "Shoppers Drug Mart\n123 King St W, Kitchener ON\n"
        "APO-METFORMIN 500 MG\nTake 1 tablet twice daily with food\n"
        "TEVA-NAPROXEN 500 MG\nTake 1 tablet at bedtime as needed for pain\n"
        "DIN: 02353377\n"
    )
    meds = parse_medications(label)
    assert len(meds) == 2
    assert [m.drug_name for m in meds] == ["APO-METFORMIN", "TEVA-NAPROXEN"]
    assert meds[0].frequency_type == "BID"
    # PRN, so no fixed reminder even though "at bedtime" also appears.
    assert meds[1].frequency_type == "PRN"
    assert meds[1].specific_times == []


def test_numbered_list_without_sig_lines_splits():
    """Enumeration with ")" markers and bare "Take ..." directions."""
    label = (
        "WATERLOO FAMILY PHARMACY\n88 Erb Street, Waterloo ON\n"
        "1) APO-METFORMIN 500 MG\nTake 1 tablet twice daily with meals\n"
        "2) RAMIPRIL 5 MG\nTake 1 capsule once daily in the morning\n"
        "3) ATORVASTATIN 20 MG\nTake 1 tablet at bedtime\n"
        "Pharmacist: J. Smith\n"
    )
    meds = parse_medications(label)
    assert [m.drug_name for m in meds] == ["APO-METFORMIN", "RAMIPRIL", "ATORVASTATIN"]
    assert [m.dosage for m in meds] == ["500MG", "5MG", "20MG"]


def test_phantom_trap_max_dose_line_does_not_become_a_second_medication():
    """"Do not exceed 4000 mg daily" carries a strength but is a limit, not
    a medication -- splitting on it would create a phantom prescription."""
    label = (
        "Shoppers Drug Mart\n123 King St W\n"
        "APO-METFORMIN 500 MG\nTake 1 tablet twice daily with food\n"
        "Do not exceed 4000 mg daily\nQty: 60  Refills: 3\n"
    )
    meds = parse_medications(label)
    assert len(meds) == 1
    assert meds[0].drug_name == "APO-METFORMIN 500 MG"


def test_phantom_trap_generic_restatement_and_total_daily_note():
    """A strength restated in parentheses on the same line, and a "Total
    5 mg per day" footer, must both stay inside one record."""
    restated = parse_medications(
        "Rexall Pharmacy\nAPO-METFORMIN 500 MG (metformin hydrochloride 500 mg)\n"
        "Take 1 tablet twice daily with food\n"
    )
    assert len(restated) == 1

    totalled = parse_medications(
        "London Drugs\nRAMIPRIL 5 MG\nTake 1 capsule once daily in the morning\n"
        "Total 5 mg per day\n"
    )
    assert len(totalled) == 1
    assert totalled[0].drug_name == "RAMIPRIL 5 MG"


def test_phantom_trap_numbered_counselling_notes_are_not_medications():
    """A numbered counselling list ("1. Avoid alcohol") is enumeration, but
    the items carry no strength and own no directions -- not medications."""
    label = (
        "Jean Coutu Pharmacie\nAMOXICILLIN 500 MG Capsules\n"
        "Take 1 capsule three times daily with food\n"
        "Patient counselling:\n1. Avoid alcohol\n2. Complete the full course\n"
    )
    meds = parse_medications(label)
    assert len(meds) == 1
    assert meds[0].drug_name == "AMOXICILLIN 500 MG Capsules"


def test_single_numbered_item_does_not_split():
    """One anchor is not a list -- both strategies require two."""
    meds = parse_medications(
        "Pharmaprix\nRx\n1. TELMISARTAN 40 MG\nSig: Take 1 tablet once daily in the morning\n"
    )
    assert len(meds) == 1


def test_prn_from_no_marker_label_gets_no_fixed_dose_time():
    """An as-needed medication must carry no scheduled reminder, matching
    the RX-marker path. Measured before the fix: frequency_type='PRN' with
    specific_times=['21:00'] -- the app invented a 9 PM dose for a
    painkiller that was prescribed only as needed."""
    meds = parse_medications(
        "CONESTOGA PHARMACY\nAcetaminophen 500mg Tablets\n"
        "Take 2 tablets every 6 hours as needed for pain or fever.\n"
        "Do not exceed 8 tablets in 24 hours.\n"
    )
    assert len(meds) == 1
    assert meds[0].frequency_type == "PRN"
    assert meds[0].time_slots == []
    assert meds[0].specific_times == []


def test_digit_frequency_wording_is_recognised():
    """"2 times a day" is ordinary label wording that only the word form
    ("twice daily") used to match, so it fell through to UNKNOWN plus the
    default morning slot -- losing the second dose."""
    meds = parse_medications("APO-METFORMIN 500 MG\nTake 1 tablet 2 times a day")
    assert meds[0].frequency_type == "BID"
    assert meds[0].time_slots == ["morning", "evening"]
    assert meds[0].specific_times == ["08:00", "18:00"]


def test_digit_and_word_frequency_forms_agree():
    """Every count wording maps to the same category and slots whichever
    form the label uses -- _PHRASE_RULES and _CATEGORY_RULES must not drift."""
    equivalents = [
        ("once a day", "1 time a day", "ONCE_DAILY"),
        ("twice daily", "2 times a day", "BID"),
        ("three times daily", "3 times per day", "TID"),
        ("four times a day", "4 times daily", "QID"),
    ]
    for word_form, digit_form, expected_type in equivalents:
        word = parse_medications(f"RAMIPRIL 5 MG\nTake 1 tablet {word_form}")[0]
        digit = parse_medications(f"RAMIPRIL 5 MG\nTake 1 tablet {digit_form}")[0]
        assert word.frequency_type == expected_type, f"{word_form!r} -> {word.frequency_type}"
        assert digit.frequency_type == expected_type, f"{digit_form!r} -> {digit.frequency_type}"
        assert word.time_slots == digit.time_slots
        assert word.specific_times == digit.specific_times


def test_postal_code_lock_dosage_regex_still_ignores_postal_codes():
    """Postal-code lock (must not regress): _DOSAGE must not false-match
    Canadian postal codes -- neither glued to a unit-like letter ("N2L 3G1")
    nor split by a space ("N2G 1A1") -- while still matching real dosage
    units."""
    assert _DOSAGE.search("N2G 1A1") is None
    assert _DOSAGE.search("N2L 3G1") is None
    assert _DOSAGE.search("500 mg") is not None
    assert _DOSAGE.search("0.4 mg") is not None
    assert _DOSAGE.search("50 mcg") is not None
