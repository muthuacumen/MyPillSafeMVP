"""Measures the LASA look-alike gate END TO END, 2026-07-30.

WHAT IS REAL HERE AND WHAT IS NOT
  * The rule is the SHIPPED one -- `app.services.lasa`, imported, not
    reimplemented. A harness that reimplements what it measures measures the
    reimplementation.
  * The search is the SHIPPED endpoint -- the live brains sidecar's
    GET /reference/search, so the real 75.0 `token_set_ratio` cutoff and the
    real 11,609-DIN profile tier are in the loop.
  * The query cleaning is the shipped `brains_client.clean_search_query`,
    reached through `lasa.label_tokens`.
  * The reference CSV is read directly for ONE purpose only: drawing the
    random brand sample for the false-fire measurement. The sidecar has no
    "list every brand" endpoint, and inventing one for a measurement would
    change the thing being measured.

HONEST PROVENANCE -- READ BEFORE QUOTING ANY NUMBER
  The token-coverage rule was designed by inspecting the two LASA pairs the
  ADR had already documented. Their 4/4 pass is therefore a CONSTRUCTION
  CHECK, not evidence that the rule generalizes. The number that is a real
  measurement is the false-fire rate on the seed-42 random sample, because
  those brands were never looked at while the rule was being written.

PREREQUISITE: the brains sidecar must be running (same as smoke_test.py /
qa_smoke_test.py / parity_check.py in dev/brains). It is NOT deployed --
it runs on the laptop over Tailscale.

    cd dev/brains && .venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
    cd dev/backend && venv/Scripts/python.exe ../../documentation/evaluation/din_lasa/probe_lasa.py
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import httpx
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "dev" / "backend"))

from app.services import lasa  # noqa: E402  -- after sys.path
from app.services.brains_client import clean_search_query  # noqa: E402

SIDECAR = os.environ.get("BRAINS_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")
PROFILE_CSV = REPO / "dev" / "brains" / "data" / "profile_reference_v1.csv"
LIMIT = 5
SAMPLE_SEED = 42
SAMPLE_BRANDS = 500
SAMPLE_GENERIC_LABELS = 200


def search(client: httpx.Client, q: str) -> list[dict]:
    """The shipped endpoint, reached the way the app reaches it.

    `clean_search_query` is NOT optional here. The app never sends raw label
    text to the sidecar -- `brains_client.search_reference` strips strength
    and dosage form first, because those tokens dilute the drug name badly
    enough to change the result. Measured while writing this probe: the raw
    query "DIGOXIN 0.125 MG" returns NOTHING (the two extra tokens drag
    `token_set_ratio` under the 75.0 cutoff) while the cleaned "DIGOXIN"
    returns digoxin products. A probe that skipped the cleaner would have
    published a false failure for a real, marketed, narrow-therapeutic-index
    drug -- and the same omission would have under-reported gating, because
    raw "ZOLTIRAX 200 MG" also falls to empty instead of surfacing ZOVIRAX.
    """
    response = client.get(
        f"{SIDECAR}/reference/search",
        params={"q": clean_search_query(q), "limit": LIMIT},
    )
    response.raise_for_status()
    rows = response.json()
    return rows if isinstance(rows, list) else []


def verdict(client: httpx.Client, label: str) -> tuple[str, list[dict]]:
    """`empty` | `gated` | `not_gated` for one label name.

    `gated` means NO candidate keeps every word the label printed -- the UI
    disables one-tap Confirm until the user acknowledges reading the label.
    """
    rows = search(client, label)
    if not rows:
        return "empty", []
    lasa.annotate_suggestions(label, rows)
    return ("not_gated" if lasa.has_covering_candidate(rows) else "gated"), rows


def run_cases(client: httpx.Client) -> dict:
    spec = json.loads((HERE / "lasa_cases.json").read_text(encoding="utf-8"))
    results, failures = [], []
    for case in spec["cases"]:
        got, rows = verdict(client, case["query"])
        ok = got in case["expect"]
        row = {
            "id": case["id"], "query": case["query"], "kind": case["kind"],
            "expected": case["expect"], "got": got, "ok": ok,
            "candidates": [
                {"product": r["product"], "din": r["din"], "score": r["score"],
                 "name_match": r["name_match"], "missing_tokens": r["missing_tokens"]}
                for r in rows
            ],
        }
        results.append(row)
        if not ok:
            failures.append(row)
    return {"n": len(results), "failures": len(failures), "cases": results}


def run_false_fire(client: httpx.Client) -> dict:
    """How often the gate fires on a label that is a REAL product name.

    Every query here names a medication that exists in the tier, so a gate is
    by definition unnecessary friction -- except where the top-5 genuinely
    contains no product carrying all of the label's words, which is a real
    (if unhelpful) answer rather than a bug.
    """
    if not PROFILE_CSV.exists():
        return {"skipped": f"missing {PROFILE_CSV}"}

    frame = pd.read_csv(PROFILE_CSV, dtype=str).fillna("")
    brands = sorted({b.upper() for b in frame["brand"].astype(str) if b.strip()})
    random.seed(SAMPLE_SEED)

    def measure(label: str, queries: list[str]) -> dict:
        counts = {"empty": 0, "gated": 0, "not_gated": 0}
        fired = []
        for q in queries:
            got, rows = verdict(client, q)
            counts[got] += 1
            if got == "gated":
                fired.append({"query": q, "top": rows[0]["product"],
                              "missing_tokens": rows[0]["missing_tokens"]})
        n = len(queries) or 1
        return {"label": label, "n": len(queries), "counts": counts,
                "gated_rate_pct": round(100 * counts["gated"] / n, 2),
                "gated_examples": fired[:15]}

    exact = measure("exact reference brands used verbatim as the label",
                    random.sample(brands, min(SAMPLE_BRANDS, len(brands))))

    # Generic-name-only labels: strip a leading manufacturer prefix, which is
    # how a label often reads when the prescriber wrote the generic.
    prefixed = [b for b in brands
                if b.split(" ")[0] in lasa.MANUFACTURER_PREFIXES
                or b.split("-")[0] in lasa.MANUFACTURER_PREFIXES]
    generic = []
    for brand in random.sample(prefixed, min(SAMPLE_GENERIC_LABELS, len(prefixed))):
        rest = brand.replace("-", " ", 1).split(" ", 1)
        if len(rest) == 2 and rest[1].strip():
            generic.append(rest[1].strip())
    generic_result = measure("generic-name-only labels (manufacturer prefix dropped)", generic)

    return {"seed": SAMPLE_SEED, "arms": [exact, generic_result]}


def main() -> int:
    with httpx.Client(timeout=20.0) as client:
        try:
            health = client.get(f"{SIDECAR}/health").json()
        except Exception as exc:  # noqa: BLE001
            print(f"sidecar not reachable at {SIDECAR}: {exc}\n"
                  f"start it first -- see this module's docstring.")
            return 2
        print(f"sidecar ok: profile_reference_rows={health.get('profile_reference_rows')}")

        cases = run_cases(client)
        print(f"\nregression cases: {cases['n'] - cases['failures']}/{cases['n']} as expected")
        for row in cases["cases"]:
            mark = "ok  " if row["ok"] else "FAIL"
            top = row["candidates"][0]["product"] if row["candidates"] else "(empty)"
            miss = row["candidates"][0]["missing_tokens"] if row["candidates"] else []
            print(f"  {mark} {row['id']:<42} {row['got']:<10} -> {top[:34]:<34} missing={miss}")

        false_fire = run_false_fire(client)
        print("\nfalse-fire measurement (seed 42):")
        for arm in false_fire.get("arms", []):
            print(f"  {arm['label']}: n={arm['n']} gated={arm['counts']['gated']} "
                  f"({arm['gated_rate_pct']}%) empty={arm['counts']['empty']}")

    out = {
        "generated": "2026-07-30",
        "sidecar_profile_rows": health.get("profile_reference_rows"),
        "rule": "app/services/lasa.py (imported, not reimplemented)",
        "search": f"{SIDECAR}/reference/search, live, cutoff 75.0 token_set_ratio",
        "provenance": ("The two documented LASA pairs are NOT held out -- the rule was "
                       "designed against them. The seed-42 false-fire rate is the fresh "
                       "measurement."),
        "regression": cases,
        "false_fire": false_fire,
    }
    (HERE / "results_lasa.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nresults -> {HERE / 'results_lasa.json'}")
    return 1 if cases["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
