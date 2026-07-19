"""Scripted Q&A smoke test for the brains sidecar (Phase 4 verification bar
#3). Run with the sidecar venv's python WHILE the service is running
(`uvicorn app:app --host 127.0.0.1 --port 8100`):

    ./.venv/Scripts/python.exe qa_smoke_test.py

Checks POST /qa/chat mode="context" for:
  1. resolved -> context_ready (warfarin food interactions) -- asserts
     packed_sources non-empty and offered_tags present.
  2. confirm
  3. pick_list
  4. not_found
  5. no_entity
  6. enumeration
  7. refused_dosing

All 7 statuses are asserted (not just reported). Report actual JSON for each.
"""
from __future__ import annotations

import json
import sys

import httpx

BASE_URL = "http://127.0.0.1:8100"
TIMEOUT = 60.0

CASES = [
    ("context_ready", "what foods should I avoid with warfarin"),
    ("confirm", "metformine side effects"),
    ("pick_list", "Is esitalopram safe for seniors?"),
    ("not_found", "can I take Coumadin with food"),
    ("no_entity", "what can I take for a headache"),
    ("enumeration", "list non-prescription products containing acetaminophen"),
    ("refused_dosing", "how much benadryl can I take"),
]


def main() -> None:
    client = httpx.Client(timeout=TIMEOUT)
    failures = 0

    for i, (expected_status, message) in enumerate(CASES, start=1):
        print(f"\n[qa-smoke] {i}/{len(CASES)} POST /qa/chat mode=context -- {message!r}")
        resp = client.post(f"{BASE_URL}/qa/chat", json={"message": message, "mode": "context"})
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status")
        print(f"[qa-smoke]   status={status!r}")

        if status != expected_status:
            print(f"[qa-smoke]   FAIL: expected status={expected_status!r}, got {status!r}")
            print(json.dumps(body, indent=2))
            failures += 1
            continue

        if status == "context_ready":
            assert body.get("packed_sources"), f"packed_sources empty: {body}"
            assert body.get("offered_tags"), f"offered_tags empty: {body}"
            print(f"[qa-smoke]   offered_tags={body['offered_tags']}")
            print(f"[qa-smoke]   packed_sources length={len(body['packed_sources'])}")
            print(f"[qa-smoke]   entity_names={body['entity_names']}")
        else:
            print(f"[qa-smoke]   answer: {body.get('answer')!r}")
            if "voice" in body:
                print(f"[qa-smoke]   voice={body['voice']}")

        print("[qa-smoke]   PASS")

    print(f"\n[qa-smoke] ==== {len(CASES) - failures}/{len(CASES)} statuses matched ====")
    if failures:
        print(f"[qa-smoke] FAILED: {failures} case(s) did not match expected status", file=sys.stderr)
        sys.exit(1)
    print("[qa-smoke] ALL STATUS ASSERTIONS PASS")


if __name__ == "__main__":
    main()
