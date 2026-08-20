"""MPR1-T09a mutation test -- prove the BLOCKER's bar can actually go red.

The T08 refutation's blocker was a bar-shaped hole, not a code-shaped one:
`/tray/analyze` persisted SB2's raw decision into the column Safety Records
colours rows from, and nothing in the suite looked at the two surfaces
together. So the repair is only real if the new bar dies when the defect comes
back. This re-introduces the verbatim persist, runs ONLY the bar that must
catch it, and writes the red output to
`tests/artifacts/MPR1-T09a/red_M5.txt`.

Same discipline as `mutation_t04.py`: the pristine source is restored in a
`finally` block and the sha256 is checked afterwards, so a crash mid-run cannot
leave a mutant in the tree.

Run:  venv/Scripts/python.exe tests/mutation_t09a.py
ASCII only.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parent.parent
ARTIFACTS = BACKEND / "tests" / "artifacts" / "MPR1-T09a"
TRAY_ROUTE = BACKEND / "app" / "api" / "v1" / "routes" / "tray.py"

MUTATIONS = [
    (
        "M5",
        "SB2's RAW decision is persisted verbatim again -- a D-7 downgraded slot "
        "lands in `analyses.decision` as `verify` and Safety Records lights it up "
        "GREEN 'matched' for a pill the tray page said not to rely on",
        TRAY_ROUTE,
        "            decision=decision,\n            abstain_action=abstain_action,",
        '            decision=slot["decision"],  # MUTANT\n'
        '            abstain_action=slot["abstain_action"],  # MUTANT',
        "tests/test_tray_slots.py::test_F1a_d7_downgraded_slot_is_never_matched_in_safety_records",
    ),
]


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    pristine = {p: p.read_bytes() for p in {TRAY_ROUTE}}
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
                f"MPR1-T09a MUTATION {mid}\n"
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
