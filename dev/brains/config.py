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

STALE AS OF THE T10/T14 RESTRUCTURE (2026-08-15): that sibling assumption no
longer holds on this machine. IMB1_v0, SB2 and BB3 all live under
`D:\\Projects\\PillSafe\\Production\\` now, while this repo is still at
`D:\\Projects\\PillSafe\\PillSafe` (it could not be moved -- a vite dev server
holds its frontend open). `start_sidecar.cmd` therefore sets IMB1_ROOT,
SB2_ROOT and BB3_ROOT explicitly, and the env var branch below is what the
running sidecar actually uses. Note the dynamic resolution does NOT check that
the path it computes exists, so without those env vars all three roots resolve
to stale locations silently -- set them, or move this repo under Production\.

Roots are inserted into `sys.path` here (at import time) so that
`import imb1` / `import sb2` work from anywhere in the sidecar process.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: T10 restructure (2026-08-15): IMB1_v0 and SB2 moved to Production\; this repo
#: (PillSafe\) could not move this window (locked by running dev processes), so
#: the sibling-of-repo-parent resolution below would land on the old (now empty)
#: locations if it ever fell through to these literal defaults. Updated to match.
#: T14 restructure (2026-08-15): BB3 moved to Production\BB3 too, and this repo
#: STILL could not move (a vite frontend dev server holds dev\frontend\node_modules
#: open). All three frozen packages now live under Production\ while this repo
#: remains at the old root, so NONE of them is a sibling of this repo's parent any
#: more -- the dynamic resolution below is wrong for all three until PillSafe\
#: itself moves under Production\. start_sidecar.cmd sets all three env vars
#: explicitly for that reason; these literals are the safety net behind them.
_LITERAL_DEFAULTS = {
    "IMB1_ROOT": r"D:\Projects\PillSafe\Production\IMB1_v0",
    "SB2_ROOT": r"D:\Projects\PillSafe\Production\SB2",
    "BB3_ROOT": r"D:\Projects\PillSafe\Production\BB3",
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

# --- M1 (2026-08-14): the two-stage imprint reader ------------------------
#
# `PILLSAFE_READER` -- master switch for `/pill/analyze`'s imprint path.
#   "off"  (DEFAULT, unchanged behaviour): call the legacy
#          `imb1.analyze_pill(photo)`. No reader, no C6 record, no `faces[]`
#          -- byte-identical to the pre-M1 sidecar.
#   "two_stage": route through `production_wiring.analyze()`, which builds ONE
#          `VerifySession` and runs A3 presence gate -> A4c constrained read.
#
# Defaulting to "off" is deliberate. The reader loads a 4-bit VLM into an
# 8.6 GB card at first request; that is a deployment decision Muthu makes by
# setting a variable, not one a code promotion makes for him.
READER_MODE = (os.environ.get("PILLSAFE_READER") or "off").strip().lower()
READER_ENABLED = READER_MODE in ("two_stage", "twostage", "on", "1", "true")

# `PILLSAFE_STAGE1` -- WHICH instrument answers Stage 1 (the presence gate).
#   "single" (DEFAULT): the SAME in-process 4.4B `Qwen/Qwen3-VL-4B-Instruct`
#          NF4 weights Stage 2 already loads, via
#          `ConstrainedScorer.generate_presence`. NB08_37 measured this ~20x
#          faster than the 8.8B incumbent while passing the safety bars, and
#          it keeps ONE model in VRAM instead of two.
#   "ollama": the 8.8B `qwen3-vl:latest` over Ollama HTTP
#          (`nb08_read16_vlm.call_a3`) -- the incumbent, kept switchable
#          because Stage 1 is a KILL-ONLY screen: it can refuse to call
#          Stage 2, never name a pill. A fallback for a kill-only screen must
#          stay one config change away.
#
# 🔴 CORRECTED 2026-08-14 (REPAIR agent, finding S6) -- WHAT `ollama` DOES NOT
# BUY YOU. It swaps STAGE 1 ONLY. `production_wiring.build_reader()` still
# evaluates `scorer or get_scorer()` on that branch, because Stage 2 (the
# constrained ranker) has no Ollama equivalent -- so `PILLSAFE_STAGE1=ollama`
# STILL loads the 4-bit NF4 scorer and STILL requires `bitsandbytes`,
# `accelerate` and a GPU. It is NOT a dependency-free fallback and must never
# be recommended as the answer to a Stage 2 load failure. The only switch that
# avoids the scorer entirely is `PILLSAFE_READER=off` above.
STAGE1_BACKEND = (os.environ.get("PILLSAFE_STAGE1") or "single").strip().lower()

# `PILLSAFE_SCORER_DEVICE` -- where Stage 2 runs. "cuda" (default) or "cpu".
# CPU is measured at ~47 s per forward pass and there are ~15 candidates per
# crop: usable only for a wiring smoke test, never for a request.
SCORER_DEVICE = (os.environ.get("PILLSAFE_SCORER_DEVICE") or "cuda").strip().lower()

for _root in (IMB1_ROOT, SB2_ROOT, BB3_ROOT):
    if _root and _root not in sys.path:
        sys.path.insert(0, _root)
