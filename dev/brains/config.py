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

# --- M1 (2026-08-14): the two-stage imprint reader -------------------------
# --- GOAL1 (2026-08-15): legacy paddle OCR path removed, "off" retired ----
# --- T06 REPAIR (2026-08-15, finding 1): closed the silent-disable loophole -
#     any value outside the valid set now raises, instead of only the
#     explicitly-retired ones -- see below.
#
# `PILLSAFE_READER` -- master switch for `/pill/analyze`'s imprint path.
#   "two_stage" (DEFAULT, since 2026-08-15): route through
#          `production_wiring.analyze()`, which builds ONE `VerifySession`
#          and runs A3 presence gate -> A4c constrained read. This is the
#          ONLY arm (owner decision 2026-08-15) -- there is no fallback
#          reader to degrade to.
#   "off"  RETIRED 2026-08-15. Used to select the legacy
#          `imb1.analyze_pill(photo)` paddle OCR dual-read subprocess path.
#          That code no longer exists in `IMB1_v0/imb1/` -- see
#          `Archive/2bdeleted/2026-08-15_paddleocr_removal/MANIFEST.md` for
#          the archived source and restore instructions. Setting
#          `PILLSAFE_READER=off` now raises at import time, below, instead of
#          silently no-opping (previously: routing into now-deleted code,
#          discovered only as a runtime ImportError mid-request).
#
# Defaulting to "two_stage" is deliberate: the reader loads a 4-bit VLM into
# an 8.6 GB card at first request, which is still a real deployment fact --
# it is simply no longer optional, since there is no second arm to fall back
# to if it is skipped.
_VALID_READER_MODES = ("two_stage", "twostage", "on", "1", "true")
_RETIRED_READER_MODES = ("off", "0", "false", "none")

# T06 REPAIR (2026-08-15, finding 1): the refuter found that ANY value not in
# _VALID_READER_MODES and not in _RETIRED_READER_MODES (a typo, stray
# whitespace, anything unrecognized) fell through BOTH checks below with no
# error and silently produced READER_ENABLED=False -- a second, undocumented
# way to disable the reader that the comments above claimed did not exist.
# Fixed by inverting the check: normalize first (unset/blank/whitespace-only
# collapse to the "two_stage" default, same as before), then require
# membership in _VALID_READER_MODES for EVERY other value -- unrecognized
# values now raise exactly like retired ones, just with a different message.
_RAW_READER_MODE = os.environ.get("PILLSAFE_READER")
READER_MODE = (_RAW_READER_MODE or "").strip().lower() or "two_stage"
if READER_MODE not in _VALID_READER_MODES:
    if READER_MODE in _RETIRED_READER_MODES:
        raise RuntimeError(
            f"PILLSAFE_READER={READER_MODE!r} is no longer a valid value. The "
            "legacy paddle OCR imprint path it selected was removed "
            "2026-08-15 (archived at "
            "Archive/2bdeleted/2026-08-15_paddleocr_removal/MANIFEST.md, "
            "which also carries restore instructions). Valid values: "
            "'two_stage' (the default; 'twostage', 'on', '1', 'true' are "
            "accepted synonyms). Unset the variable to use the default "
            "instead of disabling the reader -- there is no longer a way to "
            "disable it."
        )
    raise RuntimeError(
        f"PILLSAFE_READER={_RAW_READER_MODE!r} is not a recognized value. "
        f"Valid values: {_VALID_READER_MODES!r} (unset, empty, or "
        "whitespace-only defaults to 'two_stage'). Values that used to "
        f"disable the reader and are now retired: {_RETIRED_READER_MODES!r} "
        "-- there is no longer a way to disable it, so no other value is "
        "accepted either."
    )
# T06 REPAIR (2026-08-15, finding 1): READER_MODE is now GUARANTEED to be a
# member of _VALID_READER_MODES at this point -- every other input raised
# above instead of falling through. The valid set is a set of synonyms for
# ONE arm (there is no second arm to select), so this is a constant, not a
# computed membership test: no input can reach this line and still produce
# False. If _VALID_READER_MODES is ever trimmed to exactly {"two_stage"},
# this line does not need to change.
READER_ENABLED = True

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
# be recommended as the answer to a Stage 2 load failure.
# 🔴 UPDATED 2026-08-15 (GOAL1): there is no longer any switch that avoids the
# scorer -- `PILLSAFE_READER=off` used to, but that value is retired above
# (legacy paddle OCR path removed). The two-stage reader is the only arm.
STAGE1_BACKEND = (os.environ.get("PILLSAFE_STAGE1") or "single").strip().lower()

# `PILLSAFE_SCORER_DEVICE` -- where Stage 2 runs. "cuda" (default) or "cpu".
# CPU is measured at ~47 s per forward pass and there are ~15 candidates per
# crop: usable only for a wiring smoke test, never for a request.
SCORER_DEVICE = (os.environ.get("PILLSAFE_SCORER_DEVICE") or "cuda").strip().lower()

for _root in (IMB1_ROOT, SB2_ROOT, BB3_ROOT):
    if _root and _root not in sys.path:
        sys.path.insert(0, _root)
