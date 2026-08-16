"""Generate `dev/brains/data/profile_reference_v1.csv` -- the PROFILE tier of
PillSafe's two-tier drug reference (FixbyOPUS3 Task B1).

WHY TWO TIERS
-------------
Until this build, one table did two different jobs. `SB2/data/
ca_appearance_harmonized_v2.xlsx` (7,055 DINs) is the APPEARANCE tier: every
row has harmonized colour/shape/imprint, which is what the deterministic
matcher needs to verify a loose pill from a photo. But `/reference/search`
also used it to answer "is this medication real, and what is its DIN?" for
prescription linking -- and that question has a much bigger correct answer.
Measured on the DPD snapshot below: 11,609 marketed human DINs exist, so
4,554 of them (39%) could not be DIN-linked at all. Insulin pens, inhalers,
creams, eye drops, patches -- an entire class of a senior's medication list
was invisible to the app because it cannot be photographed as a pill.

The PROFILE tier fixes the linking question without touching the appearance
question. Everything SB2 consumes is unchanged; `/reference/search` gains
4,554 medications and a `pill_verifiable` boolean so the UI can be honest
about which of them a photo can actually check.

PROVENANCE
----------
Source (a dev-workspace file, NOT in this repo -- it is a 5.7 MB binary and
the generated CSV is the deliverable):

    D:\\Projects\\PillSafe\\data\\Pills_Patient_Access_Canada.xlsx

A Health Canada Drug Product Database (DPD) snapshot, sheet "Master List",
58,128 rows, already carrying two project-added columns
(`Pills_Patient_Access`, `PillSafe_Scope`) from the NB-era data work.

LINEAGE (asserted every run -- the script refuses to write a wrong file)
    Drug Class == "Human" AND Status == "Marketed"   -> 11,609 unique DINs
    PillSafe_Scope == "Yes"                          ->  7,055 unique DINs
    the 7,055 are a strict subset of the 11,609
    the 7,055 DIN set is IDENTICAL to SB2's appearance table's DIN set,
      which is what makes `pill_verifiable` computable from this snapshot
      alone (checked whenever the appearance workbook is readable)

REFRESH (Muthu owns this)
    1. Download a fresh DPD extract and rebuild the workbook above, keeping
       the `PillSafe_Scope` column semantics unchanged.
    2. Re-run:  dev\\brains\\.venv\\Scripts\\python.exe
                dev\\brains\\scripts\\build_profile_reference.py
    3. The lineage counts WILL move. That is expected -- the assertions
       below print the new numbers and only hard-fail on structural
       breakage (scope not a subset of marketed). Update the counts quoted
       in documentation/evaluation/rx_parsing/README.md and on
       /about/brains/prescription-reader in the same commit, or the public
       page starts quoting a number the data no longer supports.

Run:
    dev\\brains\\.venv\\Scripts\\python.exe dev\\brains\\scripts\\build_profile_reference.py
    [--source PATH] [--out PATH] [--appearance PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BRAINS_ROOT = HERE.parent

# T10 restructure (2026-08-15): `data\` moved to `Research\data\` and `SB2\` moved
# to `Production\SB2\`; this repo (`PillSafe\`) stayed put, so both used to be
# reachable via BRAINS_ROOT's sibling-of-repo-parent chain and no longer are.
# Pinned explicitly instead of derived.
DEFAULT_SOURCE = Path(r"D:\Projects\PillSafe\Research\data\Pills_Patient_Access_Canada.xlsx")
DEFAULT_OUT = BRAINS_ROOT / "data" / "profile_reference_v1.csv"
DEFAULT_APPEARANCE = Path(r"D:\Projects\PillSafe\Production\SB2\data\ca_appearance_harmonized_v2.xlsx")

SHEET = "Master List"

#: DPD column -> CSV column. `din` is emitted in SB2 token form ("DIN13803")
#: because that is the form every sidecar reference endpoint already speaks
#: and the backend converts once, at the boundary (din_utils).
COLUMN_MAP = {
    "Brand Name": "brand",
    "Company": "company",
    "Active Ingredient(s)": "ingredients",
    "Dosage Form(s)": "forms",
    "Route(s) of Administration": "routes",
    "Schedule(s)": "schedules",
}


def build(source: Path, out: Path, appearance: Path | None) -> int:
    if not source.exists():
        print(f"ERROR: DPD snapshot not found at {source}", file=sys.stderr)
        print("       (it is a dev-workspace file, deliberately not committed -- see docstring)",
              file=sys.stderr)
        return 2

    df = pd.read_excel(source, sheet_name=SHEET)
    print(f"source rows: {len(df)}")

    marketed_human = df[(df["Drug Class"] == "Human") & (df["Status"] == "Marketed")].copy()
    scope = df[df["PillSafe_Scope"] == "Yes"]

    marketed_dins = set(marketed_human["DIN"])
    scope_dins = set(scope["DIN"])
    print(f"Human AND Marketed : {len(marketed_human)} rows / {len(marketed_dins)} unique DINs")
    print(f"PillSafe_Scope=Yes : {len(scope)} rows / {len(scope_dins)} unique DINs")

    if len(marketed_human) != len(marketed_dins):
        print("ERROR: Human/Marketed rows are not unique per DIN -- refusing to write.", file=sys.stderr)
        return 2
    if not scope_dins <= marketed_dins:
        print(f"ERROR: {len(scope_dins - marketed_dins)} PillSafe_Scope DINs are not "
              "Human+Marketed -- the two tiers have diverged, refusing to write.", file=sys.stderr)
        return 2

    marketed_human["din"] = "DIN" + marketed_human["DIN"].astype(int).astype(str)
    marketed_human["pill_verifiable"] = marketed_human["DIN"].isin(scope_dins)

    if appearance is not None and appearance.exists():
        appearance_dins = set(
            pd.read_excel(appearance, sheet_name="harmonized")["din"].astype(str)
        )
        verifiable_dins = set(marketed_human.loc[marketed_human["pill_verifiable"], "din"])
        if verifiable_dins != appearance_dins:
            print(
                "ERROR: pill_verifiable set != SB2 appearance-table DIN set "
                f"(+{len(verifiable_dins - appearance_dins)} / "
                f"-{len(appearance_dins - verifiable_dins)}) -- refusing to write a "
                "reference whose badge would lie about what a photo can check.",
                file=sys.stderr,
            )
            return 2
        print(f"appearance cross-check: OK ({len(appearance_dins)} DINs, exact set match)")
    else:
        print(f"appearance cross-check: SKIPPED (workbook not readable at {appearance})")

    out_df = marketed_human.rename(columns=COLUMN_MAP)[
        ["din", *COLUMN_MAP.values(), "pill_verifiable"]
    ].sort_values("din", key=lambda s: s.str[3:].astype(int))

    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False, encoding="utf-8")
    print(f"wrote {len(out_df)} rows ({int(out_df['pill_verifiable'].sum())} pill-verifiable) -> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--appearance", type=Path, default=DEFAULT_APPEARANCE)
    args = ap.parse_args()
    return build(args.source, args.out, args.appearance)


if __name__ == "__main__":
    raise SystemExit(main())
