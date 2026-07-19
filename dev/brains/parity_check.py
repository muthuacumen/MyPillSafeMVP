"""Parity check (Phase 4 verification bar #2): proves `qa.chat_context()`
mirrors `BB3Engine.chat()`'s pre-generation control flow exactly for every
short-circuit status. Run with the sidecar venv's python, from this
directory (needs Ollama up so `BB3Engine()` can construct):

    ./.venv/Scripts/python.exe parity_check.py

For each case below, calls BOTH `BB3Engine.chat()` and `qa.chat_context()`
against the SAME store connection and asserts `status`, `answer`, and
`resolution` are equal (ignoring `latency_s`, which is a fresh per-call
timer and expected to differ). Prints PASS/FAIL per case and a final
summary; exits non-zero if anything differs.
"""
from __future__ import annotations

import sys

import config  # noqa: F401 -- sys.path side effect
import qa
from bb3 import store
from bb3.engine import BB3Engine

CASES = [
    ("confirm", "metformine side effects", None, None),
    ("pick_list", "Is esitalopram safe for seniors?", None, None),
    ("not_found", "can I take Coumadin with food", None, None),
    ("no_entity", "what can I take for a headache", None, None),
    ("enumeration", "list non-prescription products containing acetaminophen", None, None),
    ("refused_dosing", "how much benadryl can I take", None, None),
]

COMPARE_KEYS = ["status", "answer", "resolution"]


def main() -> int:
    con = store.connect(readonly=True)
    engine = BB3Engine(con=con)

    failures = 0
    for expected_status, message, din, confirmed_name in CASES:
        chat_result = engine.chat(message, din=din, confirmed_name=confirmed_name)
        context_result = qa.chat_context(message, din=din, confirmed_name=confirmed_name)

        diffs = []
        for key in COMPARE_KEYS:
            if chat_result.get(key) != context_result.get(key):
                diffs.append(f"    {key}: chat()={chat_result.get(key)!r}  context()={context_result.get(key)!r}")

        status_ok = chat_result["status"] == expected_status == context_result["status"]
        if diffs or not status_ok:
            failures += 1
            print(f"FAIL [{expected_status}] {message!r}")
            if not status_ok:
                print(f"    expected status={expected_status!r}, chat()={chat_result['status']!r}, "
                      f"context()={context_result['status']!r}")
            for d in diffs:
                print(d)
        else:
            print(f"PASS [{expected_status}] {message!r}")

    print()
    if failures:
        print(f"{failures}/{len(CASES)} cases FAILED -- diff is NOT empty.")
        return 1
    print(f"All {len(CASES)} cases match (status/answer/resolution identical, latency_s ignored). Diff is empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
