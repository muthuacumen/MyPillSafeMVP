"""Multi-drug splitter probe set.

Measures how many prescription records `parse_medications` produces for a
range of realistic Canadian label shapes, against the expected count.

Two failure classes are reported separately because they are NOT equally
bad in a medication-safety app:
  * MISSED  - fewer records than meds on the label (a med is lost)
  * PHANTOM - more records than meds on the label (a spurious prescription
              and a spurious reminder)

Run before and after the splitter change; the delta is the evidence.
"""
import sys

sys.path.insert(0, r"D:\Projects\PillSafe\PillSafe\dev\backend")

from app.services.prescription_parser import parse_medications  # noqa: E402

# (id, expected_count, expected_name_fragments_or_None, label_text)
CASES = [
    (
        "A-numbered-sig-5med (the real synthetic doc's shape)",
        5,
        ["tylenol", "advil", "benadryl", "pepcid", "allergy"],
        """\
Conestoga Family Health Clinic
123 Health Street, Kitchener, ON  N2G 1A1
Tel: (519) 555-0134    Fax: (519) 555-0135
Patient: Muthuraj Jayakumar
Prescriber: Dr. A. Reyes, MD
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
Notes: Patient counselled on OTC interactions.
Dr. A. Reyes
""",
    ),
    (
        "B-numbered-no-sig-3med",
        3,
        ["metformin", "ramipril", "atorvastatin"],
        """\
WATERLOO FAMILY PHARMACY
88 Erb Street, Waterloo ON
1) APO-METFORMIN 500 MG
Take 1 tablet twice daily with meals
2) RAMIPRIL 5 MG
Take 1 capsule once daily in the morning
3) ATORVASTATIN 20 MG
Take 1 tablet at bedtime
Pharmacist: J. Smith
""",
    ),
    (
        "C-unenumerated-stacked-2med (dosage fallback must catch)",
        2,
        ["metformin", "naproxen"],
        """\
Shoppers Drug Mart
123 King St W, Kitchener ON
APO-METFORMIN 500 MG
Take 1 tablet twice daily with food
TEVA-NAPROXEN 500 MG
Take 1 tablet at bedtime as needed for pain
DIN: 02353377
""",
    ),
    (
        "D-PHANTOM-TRAP single med + mg max-dose line",
        1,
        ["metformin"],
        """\
Shoppers Drug Mart
123 King St W
APO-METFORMIN 500 MG
Take 1 tablet twice daily with food
Do not exceed 4000 mg daily
Qty: 60  Refills: 3
""",
    ),
    (
        "E-PHANTOM-TRAP single med + generic-name restatement",
        1,
        ["metformin"],
        """\
Rexall Pharmacy
APO-METFORMIN 500 MG (metformin hydrochloride 500 mg)
Take 1 tablet twice daily with food
""",
    ),
    (
        "F-PHANTOM-TRAP single med + total-daily note",
        1,
        ["ramipril"],
        """\
London Drugs
RAMIPRIL 5 MG
Take 1 capsule once daily in the morning
Total 5 mg per day
""",
    ),
    (
        "G-PHANTOM-TRAP numbered counselling notes, single med",
        1,
        ["amoxicillin"],
        """\
Jean Coutu Pharmacie
AMOXICILLIN 500 MG Capsules
Take 1 capsule three times daily with food
Patient counselling:
1. Avoid alcohol
2. Complete the full course
""",
    ),
    (
        "H-PHANTOM-TRAP garbled 1000+ char dump, single med",
        1,
        ["amoxicillin"],
        ("SPOT HOSPITAL PHARMACY DIVISION RECEIPT CODE 998877 " * 20 + "\n") * 3
        + "Amoxicillin 500mg Capsules\n"
        + "Take 1 capsule three times daily with food for infection\n"
        + ("SPOT HOSPITAL PHARMACY DIVISION RECEIPT CODE 998877 " * 20 + "\n") * 10,
    ),
    (
        "I-single-numbered-item (1 anchor only, must not split)",
        1,
        ["telmisartan"],
        """\
Pharmaprix
Rx
1. TELMISARTAN 40 MG
Sig: Take 1 tablet once daily in the morning
""",
    ),
    (
        "J-clock-times-2med",
        2,
        ["atorvastatin", "metformin"],
        """\
Costco Pharmacy
ATORVASTATIN 20 MG
Take 1 tablet at 8:00 AM and 8:00 PM
APO-METFORMIN 500 MG
Take 1 tablet 2 times a day
""",
    ),
    (
        "K-single-med-classic (must stay 1, unchanged)",
        1,
        ["acetaminophen"],
        """\
CONESTOGA PHARMACY
123 University Avenue West, Waterloo, ON N2L 3G1
Tel: (519) 888-4567 | Fax: (519) 888-4568
www.conestogapharmacy.ca
Acetaminophen 500mg Tablets
Take 2 tablets every 6 hours as needed for pain or fever.
Do not exceed 8 tablets in 24 hours.
Qty: 100  Refills: 2
DIN: 00559407
""",
    ),
    (
        "L-demo-text (OCR_PIPELINE_ENABLED=false path, must stay 1)",
        1,
        ["metformin"],
        "Metformin HCl 500mg \u2014 twice daily with meals. Dr. A. Chen. Refills: 2.",
    ),
]


def main() -> int:
    missed = phantom = name_wrong = 0
    print(f"{'case':<52} {'exp':>4} {'got':>4}  verdict")
    print("-" * 96)
    for case_id, expected, fragments, text in CASES:
        meds = parse_medications(text)
        got = len(meds)
        names = [m.drug_name for m in meds]
        if got < expected:
            verdict = "MISSED"
            missed += 1
        elif got > expected:
            verdict = "PHANTOM"
            phantom += 1
        else:
            verdict = "count-ok"
        if fragments and got == expected:
            joined = " | ".join(names).lower()
            bad = [f for f in fragments if f not in joined]
            if bad:
                verdict = f"NAME-WRONG missing={bad}"
                name_wrong += 1
        print(f"{case_id:<52} {expected:>4} {got:>4}  {verdict}")
        for m in meds:
            print(
                f"{'':<52} -> {m.drug_name!r} dosage={m.dosage!r} "
                f"type={m.frequency_type} slots={m.time_slots} times={m.specific_times}"
            )
    total = len(CASES)
    print("-" * 96)
    print(
        f"cases={total}  missed={missed}  phantom={phantom}  name_wrong={name_wrong}  "
        f"fully_correct={total - missed - phantom - name_wrong}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
