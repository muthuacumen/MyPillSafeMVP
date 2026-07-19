"""Brains sidecar configuration.

Env-overridable roots for the frozen brain packages (IMB1_v0, SB2, BB3 —
BB3 wired in Phase 4 via `qa.py` / the `/qa/*` endpoints). Defaults are
computed as siblings of this repo's
parent directory (`D:\\Projects\\PillSafe\\PillSafe` -> parent
`D:\\Projects\\PillSafe` -> siblings `IMB1_v0`, `SB2`, `BB3`), so the
service works out of the box on the machine it was built on without
hardcoding a drive letter, while still falling back to the literal
defaults if that resolution fails for any reason (e.g. this file gets
moved/copied somewhere the repo layout assumption doesn't hold).

Roots are inserted into `sys.path` here (at import time) so that
`import imb1` / `import sb2` work from anywhere in the sidecar process.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_LITERAL_DEFAULTS = {
    "IMB1_ROOT": r"D:\Projects\PillSafe\IMB1_v0",
    "SB2_ROOT": r"D:\Projects\PillSafe\SB2",
    "BB3_ROOT": r"D:\Projects\PillSafe\BB3",
}


def _default_root(pkg_dirname: str, literal_fallback: str) -> str:
    """Sibling-of-repo-parent resolution, falling back to the literal default.

    This file lives at `<repo>/dev/brains/config.py`. `<repo>`'s parent
    directory is where the frozen packages live as siblings of the repo
    itself (e.g. `D:\\Projects\\PillSafe\\{PillSafe, IMB1_v0, SB2, BB3}`).
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]  # .../dev/brains/config.py -> repo root
        candidate = repo_root.parent / pkg_dirname
        return str(candidate)
    except Exception:
        return literal_fallback


IMB1_ROOT = os.environ.get("IMB1_ROOT") or _default_root("IMB1_v0", _LITERAL_DEFAULTS["IMB1_ROOT"])
SB2_ROOT = os.environ.get("SB2_ROOT") or _default_root("SB2", _LITERAL_DEFAULTS["SB2_ROOT"])
BB3_ROOT = os.environ.get("BB3_ROOT") or _default_root("BB3", _LITERAL_DEFAULTS["BB3_ROOT"])
BRAINS_PORT = int(os.environ.get("BRAINS_PORT", "8100"))

for _root in (IMB1_ROOT, SB2_ROOT, BB3_ROOT):
    if _root and _root not in sys.path:
        sys.path.insert(0, _root)
