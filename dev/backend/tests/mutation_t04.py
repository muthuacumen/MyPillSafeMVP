"""MPR1-T04 mutation test -- prove the bars can actually go red.

A green suite proves nothing until you have watched it fail for the right
reason. This injects three defects, one at a time, into the code the bars are
supposed to guard, runs ONLY the bar that must catch each one, and writes the
red output to `tests/artifacts/MPR1-T04/red_M<n>.txt`.

The pristine source is restored in a `finally` block and the sha256 is checked
afterwards, so a crash mid-run cannot leave a mutant in the tree.

Run:  venv/Scripts/python.exe tests/mutation_t04.py
ASCII only.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parent.parent
ARTIFACTS = BACKEND / "tests" / "artifacts" / "MPR1-T04"
TRAY_ROUTE = BACKEND / "app" / "api" / "v1" / "routes" / "tray.py"
TRAY_MSGS = BACKEND / "app" / "services" / "tray_messages.py"

MUTATIONS = [
    (
        "M1",
        "slot = well (the +1 dropped) -- the frontend would label every slot one low",
        TRAY_MSGS,
        "    slot = int(index) + 1 if isinstance(index, int) else None",
        "    slot = int(index) if isinstance(index, int) else None",
        "tests/test_tray_slots.py::test_B01_slot_mapping_well_k_to_slot_k_plus_1",
    ),
    (
        "M2",
        "the UNFILTERED profile is sent to the sidecar -- an excluded medication "
        "becomes scoreable, and therefore verifiable",
        TRAY_ROUTE,
        "    supported_tokens = allowlist.supported_subset(profile_dins)",
        "    supported_tokens = list(profile_dins)",
        "tests/test_tray_slots.py::test_B13_excluded_din_never_sent_and_notice_emitted",
    ),
    (
        "M3",
        "none_route is ignored and NONE is always terminal -- Muthu's filed tray "
        "call (3) silently reverted",
        TRAY_MSGS,
        "        if none_route == NoneRoute.RETRY:",
        "        if False:  # MUTANT",
        "tests/test_tray_slots.py::test_B09_none_faces_retry_route_default",
    ),
    (
        "M4",
        "the D-7 fail-safe downgrade is skipped -- a record that fails C6 validation "
        "reaches the patient as a green `verify`",
        TRAY_MSGS,
        "    if contract_error:\n        out.update(verdict=Verdict.ERROR,",
        "    if False:  # MUTANT (D-7 downgrade skipped)\n        out.update(verdict=Verdict.ERROR,",
        "tests/test_tray_slots.py::test_D7a_contract_error_downgrades_sb2_verify",
    ),
]


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    pristine = {p: p.read_bytes() for p in {TRAY_ROUTE, TRAY_MSGS}}
    pristine_sha = {p: _sha(p) for p in pristine}
    results = []
    try:
        for mid, desc, path, old, new, bar in MUTATIONS:
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                print(f"[{mid}] ABORT: anchor found {text.count(old)} times in {path.name}")
                return 2
            path.write_text(text.replace(old, new), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", bar, "-q", "--no-header", "-p", "no:cacheprovider"],
                cwd=BACKEND, capture_output=True, text=True,
            )
            path.write_bytes(pristine[path])
            red = proc.returncode != 0
            out = ARTIFACTS / f"red_{mid}.txt"
            out.write_text(
                f"MPR1-T04 MUTATION {mid}\n"
                f"defect  : {desc}\n"
                f"file    : {path.relative_to(BACKEND)}\n"
                f"replaced: {old.strip()}\n"
                f"with    : {new.strip()}\n"
                f"bar     : {bar}\n"
                f"exit    : {proc.returncode} ({'RED (expected)' if red else 'GREEN -- BAR IS BLIND'})\n"
                f"{'=' * 78}\n{proc.stdout}\n{proc.stderr}\n",
                encoding="utf-8",
            )
            results.append((mid, red, out))
            print(f"[{mid}] {'RED   ' if red else 'GREEN!'} {bar.split('::')[-1]} -> {out.name}")
    finally:
        for path, blob in pristine.items():
            path.write_bytes(blob)
        for path, sha in pristine_sha.items():
            assert _sha(path) == sha, f"FAILED TO RESTORE {path}"
        print("restored: sha256 verified for", ", ".join(p.name for p in pristine))

    reds = sum(1 for _, red, _ in results if red)
    print(f"\n{reds}/{len(MUTATIONS)} mutations produced a red bar")
    return 0 if reds == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
