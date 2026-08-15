"""Standalone smoke test for the brains sidecar.

Run with the sidecar venv's python WHILE the service is running
(`uvicorn app:app --host 127.0.0.1 --port 8100`):

    ./.venv/Scripts/python.exe smoke_test.py

Checks (in order):
  1. GET /health -- asserts the service reports itself ok.
  2. GET /reference/search?q=GRAVOL -- asserts >=1 result, prints top 3.
  3. GET /reference/candidates for the top search hit's DIN -- asserts >=1 row.
  4. POST /pill/analyze for 2 real OTC photos that verified in the frozen
     NB07 eval (picked dynamically from
     IMB1_Prototype/results/08_derisk_imprint_up_per_photo.csv, resolved
     under Brainstorm/OTC_Images/Raw/), each with a 3-DIN profile_dins list
     containing that photo's own DIN. Response SHAPE is asserted strictly;
     the actual decision (verify/reject/abstain) is reported, NOT asserted --
     these photos verified in the frozen offline eval, but the matcher's
     committed operating point is safety-biased (abstain is the common case
     by design), so re-verifying live over HTTP is not guaranteed.

First calls are slow (model load + Paddle subprocess spawn) -- timeouts here
are generous (200s) per the sidecar's own latency characteristics.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8100"
TIMEOUT = 200.0

CSV_PATH = Path(r"D:\Projects\PillSafe\IMB1_Prototype\results\08_derisk_imprint_up_per_photo.csv")
RAW_DIR = Path(r"D:\Projects\PillSafe\Brainstorm\OTC_Images\Raw")

# Filler DINs for the 3-DIN profile list (real reference rows, so a
# realistic-looking profile) -- swapped out below if either collides with
# the photo's own DIN.
_FILLER_DINS = ["DIN4596", "DIN13285", "DIN12750"]


def _pick_verified_photos(n: int = 2) -> list[dict]:
    """Read the frozen NB07 derisk CSV, find rows that verified, resolve
    each candidate's photo path under Raw/, and return the first `n` with
    distinct DINs whose photo file actually exists on disk."""
    with CSV_PATH.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        print(f"[smoke] CSV columns: {fieldnames}")

        if "verified" in fieldnames:
            def is_verified(row: dict) -> bool:
                return str(row["verified"]).strip().lower() in ("true", "1", "yes")
        elif "decision" in fieldnames:
            def is_verified(row: dict) -> bool:
                return row["decision"].strip().lower() == "verify"
        else:
            raise RuntimeError(f"CSV has neither a 'verified' nor 'decision' column: {fieldnames}")

        rows = list(reader)

    picked: list[dict] = []
    seen_dins: set[str] = set()
    for row in rows:
        if not is_verified(row):
            continue
        din8 = row.get("din8", "").strip()
        if not din8 or din8 in seen_dins:
            continue
        photo_path = RAW_DIR / row["photo"]
        if not photo_path.exists():
            continue
        din_norm = f"DIN{int(float(din8))}"
        picked.append({"photo_path": photo_path, "din": din_norm, "row": row})
        seen_dins.add(din8)
        if len(picked) >= n:
            break

    if len(picked) < n:
        raise RuntimeError(f"Could only find {len(picked)} verified photos with resolvable paths (needed {n})")
    return picked


def main() -> None:
    client = httpx.Client(timeout=TIMEOUT)
    failures = 0

    # --- 1. /health ---
    print("\n[smoke] 1/4 GET /health")
    resp = client.get(f"{BASE_URL}/health")
    resp.raise_for_status()
    health = resp.json()
    print(json.dumps(health, indent=2))
    assert health["status"] == "ok", f"health status not ok: {health}"
    assert health["imb1_ok"] is True, f"imb1 not ok: {health['imb1_ok']}"
    assert health["sb2_ok"] is True, f"sb2 not ok: {health['sb2_ok']}"
    print("[smoke] health OK")

    # --- 2. /reference/search ---
    print("\n[smoke] 2/4 GET /reference/search?q=GRAVOL")
    resp = client.get(f"{BASE_URL}/reference/search", params={"q": "GRAVOL", "limit": 10})
    resp.raise_for_status()
    search_results = resp.json()
    assert len(search_results) >= 1, f"expected >=1 search result, got {search_results}"
    print(f"[smoke] {len(search_results)} results, top 3:")
    for r in search_results[:3]:
        print(f"    {r}")
    top_din = search_results[0]["din"]

    # --- 3. /reference/candidates ---
    print(f"\n[smoke] 3/4 GET /reference/candidates?dins={top_din}")
    resp = client.get(f"{BASE_URL}/reference/candidates", params={"dins": top_din})
    resp.raise_for_status()
    candidates = resp.json()
    assert len(candidates) >= 1, f"expected >=1 candidate row for {top_din}, got {candidates}"
    print(f"[smoke] {len(candidates)} candidate row(s) for {top_din}:")
    for c in candidates:
        print(f"    {c}")

    # --- 4. /pill/analyze on 2 real photos ---
    print("\n[smoke] 4/4 POST /pill/analyze on 2 real OTC photos (verified in frozen NB07 eval)")
    picked = _pick_verified_photos(2)
    decisions_report = []

    for item in picked:
        photo_path: Path = item["photo_path"]
        din = item["din"]
        fillers = [f for f in _FILLER_DINS if f != din][:2]
        profile_dins = [din] + fillers

        print(f"\n[smoke] analyzing {photo_path.name} (own DIN {din}, profile={profile_dins})")
        with photo_path.open("rb") as fh:
            files = {"image": (photo_path.name, fh, "image/jpeg")}
            data = {"profile_dins": json.dumps(profile_dins)}
            resp = client.post(f"{BASE_URL}/pill/analyze", files=files, data=data)
        resp.raise_for_status()
        body = resp.json()

        # --- strict shape assertions ---
        # GOAL1 (2026-08-15): the legacy `imprint_reads` key no longer exists
        # anywhere -- the paddle OCR path that produced it was removed (archived
        # in Archive/2bdeleted/2026-08-15_paddleocr_removal). This now asserts
        # the C6 contract shape instead: `contract_version` present, and
        # `faces` present as a list (populated when the two-stage reader is
        # armed and a profile was supplied; empty otherwise -- see
        # `nb08_imb1.build_record`'s own docstring for why an empty list means
        # UNKNOWN, not a terminal no-imprint verdict).
        record = body.get("record")
        assert record is not None, f"missing record in response: {body}"
        for key in ("detected", "contract_version", "colour_modes", "shape_out", "type_out", "faces"):
            assert key in record, f"record missing key {key!r}: {record}"
        assert isinstance(record["faces"], list), f"record['faces'] should be a list: {record['faces']!r}"

        match = body.get("match")
        assert match is not None, f"expected a match (profile_dins was non-empty): {body}"
        assert match["decision"] in ("verify", "reject", "abstain"), f"unexpected decision: {match['decision']}"
        assert "ranked_candidates" in match, f"match missing ranked_candidates: {match}"
        assert "disclaimer" in match, f"match missing disclaimer: {match}"

        print(f"[smoke] detected={record['detected']} decision={match['decision']} matched_din={match.get('matched_din')}")
        print(f"[smoke] disclaimer: {match['disclaimer']}")
        if match["ranked_candidates"]:
            print(f"[smoke] top ranked_candidate: {match['ranked_candidates'][0]}")

        decisions_report.append({
            "photo": photo_path.name,
            "own_din": din,
            "profile_dins": profile_dins,
            "decision": match["decision"],
            "matched_din": match.get("matched_din"),
            "top_ranked_candidate": match["ranked_candidates"][0] if match["ranked_candidates"] else None,
        })

    print("\n[smoke] ==== decisions summary (reported, not asserted) ====")
    for d in decisions_report:
        print(json.dumps(d, indent=2, default=str))

    print("\n[smoke] ALL SHAPE ASSERTIONS PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\n[smoke] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n[smoke] ERROR: {exc!r}", file=sys.stderr)
        raise
