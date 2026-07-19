"""Unit tests for the multi-medication OCR text parser (no DB/HTTP)."""
from app.services.prescription_parser import parse_medications

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
