"""STEP 7b -- the PRODUCTION CALLER for the `label_to_din` map.

This is the standing `PRODUCTION_WIRING: OWED` item finally discharged.
Wires `app.py`'s `/pill/analyze` endpoint to `NB08_Notebook/src/nb08_verify.py
::VerifySession` -- the composition object STEP 7b built to own ONE
`Lexicon` for both the reader's ballot and SB2's `label_to_din` map (see
that module's docstring for the object itself; this file is only the
CALLER, per NB08_C6_Contract_Build.md section 8 "STEP 7b" 7b.8 Q4).

WHY A SEPARATE MODULE, NOT INLINE IN app.py
--------------------------------------------
`app.py` imports `imb1`/`fastapi`/`torch` at module load -- heavy, and only
importable from the sidecar venv (`dev/brains/.venv`). The wiring decision
itself (which `sb2` is active, whether it can take a map, whether a
`VerifySession` can be built) needs none of that: it is control flow over
objects the caller already resolved. Kept here so it is bar- and
mutation-tested directly (`harness/NB08_C6/test_production_wiring.py`, run
from plain `python`, no torch/fastapi needed) and so app.py's own diff for
this step is a two-line call-site change (see `decide()`'s docstring).

THE CAPABILITY GATE THIS FILE ADDS -- and what production `SB2/` can do TODAY
----------------------------------------------------------------------------
🔴 CORRECTED 2026-08-14 (REPAIR agent, finding S5). The block that stood
here described the tree as it was on 2026-08-13, the day BEFORE the L4a
promotion, and it was left standing after the promotion landed. Every
sentence in it is now false, and a shipped docstring that mis-describes the
module it ships with is a defect, not a stale note. The superseded text
claimed: production `SB2/sb2.match_pill` takes no `label_to_din` keyword,
there is no `c6_adapter.py`, no `c6_flip.py`, `matcher.py` is 415 lines,
`sb2.matcher.flip_suppressed` is undefined, and "L4a IS NOT YET DONE".

RE-MEASURED 2026-08-14 in the sidecar venv, by importing what `config.py`
actually resolves (`SB2_ROOT` = `D:\\Projects\\PillSafe\\SB2`), not by
reading a diff:

    sb2.__file__                       D:\\Projects\\PillSafe\\SB2\\sb2\\__init__.py
    inspect.signature(match_pill)      (record, profile_dins, label_to_din)
    sb2.matcher.flip_suppressed        DEFINED (matcher.py:648)
    sb2/c6_adapter.py, sb2/c6_flip.py  BOTH PRESENT
    matcher.py                         1407 lines
    sb2.C6_ADAPTER                     True
    build_verify_session(4 real DINs)  SUCCEEDS -> lexicon_id lx_7ae092,
                                       label_to_din over 4 labels

So BOTH of the two failure modes the old text described are gone, L4a IS
done, and the wired path -- not the fallback -- is what a real request now
takes (W3/W3REAL measure `LAST_DECISION_SOURCE == "wired_session"` 3/3).

The capability CHECK below stays exactly as it was, and that is deliberate:
it asks the imported `match_pill` what it accepts instead of hardcoding a
path or a date, so it keeps working across a rollback, an `SB2_ROOT`
override, or a machine where the promotion has not landed. What changed is
the world it reports on, not the code. `build_verify_session` likewise
stays defensively wrapped -- a moved allowlist, an unreadable workbook or an
absent `nb08_verify` must still degrade to the legacy answer rather than
turn a request that used to succeed into a 500.

WHAT THIS DOES NOT DO -- the app-photo calibration gap stays OPEN
---------------------------------------------------------------------
UPDATED 2026-08-15 (GOAL1 -- legacy paddle OCR removal), re-landed 2026-08-18
after a 2026-08-15/16 rollback + interim restore (see
`archive/2bdeleted/2026-08-15_paddleocr_removal/MANIFEST.md`). `imb1.analyze_pill()`
(production `IMB1_v0`) no longer spawns the legacy paddle subprocess and no
longer returns an `imprint_reads` key at all -- that code is deleted, archived
in `archive/2bdeleted/2026-08-15_paddleocr_removal` (re-confirmed removed
2026-08-18). It still returns the pre-C6 appearance-only shape
(`colour_modes`/`shape_out`/`type_out`, no `contract_version`, no `faces`),
because THIS module never calls it directly. `sb2.match_pill` branches on
`record.get("contract_version") == "C6"`; that legacy-ish shape never reaches
that branch. `PILLSAFE_READER=off` can no longer select this path -- it is
retired and fails fast at config load (`config.py`) -- but `app.py`'s
`/pill/analyze` still calls `imb1.analyze_pill()` directly, bypassing this
module and `analyze()` below entirely, whenever `profile_dins` is empty (no
patient profile to build a lexicon from). What M1 changed is that `analyze()`
below produces a REAL C6 record whenever a profile IS supplied, which is what
finally makes the map EFFECTIVE rather than merely reachable. The remaining
half of open item 9 is CALIBRATION, not reachability: the frozen gate was
fitted on tray-cut crops and the app cuts with a FastSAM bbox, and that
geometry difference is unmeasured. See `LAST_DECISION_SOURCE` for a way to
tell which of the three paths a given call actually took.

ASCII ONLY. The cp1252 console-print trap has recurred in this project.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Optional

#: This file lives at `<repo>/dev/brains/production_wiring.py`, a sibling of
#: `app.py`/`config.py`. Originally `<repo>`'s parent is where `IMB1_Prototype/`
#: lived as a sibling of the repo itself -- the SAME sibling-of-repo-parent
#: convention `config.py` uses for IMB1_ROOT/SB2_ROOT/BB3_ROOT.
#:
#: T10 restructure (2026-08-15): `IMB1_Prototype/` moved to `Research/` while
#: this repo (`PillSafe/`) could not move (locked by running dev processes) --
#: so the sibling assumption breaks here. Pinned explicitly instead.
#: MPR1-T30 (2026-08-20), T29 sections 3.1/4.3: the closure was PROMOTED into
#: `Production\NB08_Runtime\`, so this no longer reaches into `Research\`.
#: `nb08_runtime` resolves the promoted tree (env-overridable, fail-loud) and
#: binds it as a PACKAGE -- it deliberately does NOT put it on `sys.path`; see
#: the `sys.path.append` this replaced, below.
_PILLSAFE_PARENT = Path(__file__).resolve().parents[3]
import nb08_runtime  # noqa: E402

NB08_SRC = nb08_runtime.NB08_SRC
ALLOWLIST_CSV = NB08_SRC.parent / "data" / "allowlist" / "supported_dins.csv"

#: Diagnostic only, never read by any decision logic -- which of the three
#: paths the MOST RECENT `decide()` call actually took. Exists so a
#: verification script can MEASURE reachability instead of assuming it from
#: a response shape alone (a legacy record's `match` dict looks identical
#: whether or not a map was supplied -- see the module docstring's "what
#: this does not do").
LAST_DECISION_SOURCE: str = ""

VERIFY_SESSION_IMPORT_ERROR: Optional[str] = None
try:
    # MPR1-T30 (2026-08-20), T29 section 4.3 -- this used to be
    # `sys.path.append(str(NB08_SRC))`. The append was correct and MEASURED:
    # `NB08_SRC` contains `colour.py`, which shadows the third-party
    # `colour`/`colour-science` package the moment it sits ahead of
    # site-packages on `sys.path`. `IMB1_v0/imb1/colour.py` does its own
    # deferred `import colour as colour_science` mid-pipeline (reached for
    # a non-neutral pill); with `NB08_SRC` inserted at position 0 this
    # turned a working `imb1.analyze_pill()` call into `AttributeError:
    # module 'colour' has no attribute 'CCS_ILLUMINANTS'` the first time
    # this module was imported into the real sidecar process.
    #
    # Appending was ORDERING-dependent, though: any later `insert(0, ...)`
    # anywhere in the process re-arms it, and two closure modules already do
    # one. `nb08_runtime` (imported above) removes the ordering question
    # entirely -- the directory is NEVER on `sys.path`, and only the
    # enumerated `nb08_*` names are bound onto it, with `colour` deliberately
    # NOT among them. `nb08_verify` below resolves through that binding.
    from nb08_verify import VerifySession  # noqa: E402
except Exception as exc:  # pragma: no cover - defensive, see module docstring
    VerifySession = None  # type: ignore[assignment]
    VERIFY_SESSION_IMPORT_ERROR = repr(exc)

__all__ = [
    "decide", "sb2_match_pill_accepts_label_map", "build_verify_session",
    "VerifySession", "VERIFY_SESSION_IMPORT_ERROR", "ALLOWLIST_CSV", "NB08_SRC",
    "LAST_DECISION_SOURCE",
    "analyze", "build_reader", "get_scorer", "reader_backend_report",
    "SCORER_LOAD_ERROR", "ReaderError", "READER_ERROR_CODE", "LAST_READ_ATTEMPTS",
]

#: The `detail["error"]["code"]` `app.py` puts on the 422 raised for a
#: `ReaderError`. Distinct from the generic `PILL_ANALYSIS_FAILED` so an
#: operator reading a log can tell "the armed reader failed on this request"
#: apart from "the vision stage could not analyse this photo" -- the two have
#: completely different remedies (VRAM/config vs the photograph itself).
READER_ERROR_CODE = "READER_ERROR_RETRYABLE"


class ReaderError(RuntimeError):
    """The ARMED read failed for this request, after one retry (S7).

    Carries `attempts` and the original exception (`__cause__`). `app.py`
    catches this specifically -- BEFORE its generic `except Exception` -- and
    maps it to the SAME 422 the generic handler uses, with the distinct
    `READER_ERROR_CODE` detail string.

    🔴 WHY THIS IS NOT A FALLBACK TO THE LEGACY READER. The obvious "repair"
    -- catch the reader failure and re-run `imb1.analyze_pill(photo)` so the
    patient still gets an answer -- is REFUSED on purpose. The legacy path's
    imprint comes from PaddleOCR free-text, the fabrication-prone route the
    whole two-stage design exists to replace; silently substituting it when
    the constrained reader dies would make the WORSE instrument the one that
    answers exactly when something is already wrong, and nothing in the
    response would say which instrument spoke. An armed sidecar that cannot
    read refuses the request. Falling back to `off` is a DEPLOYMENT decision
    (`PILLSAFE_READER`), not a per-request one.
    """

    def __init__(self, message: str, *, attempts: int = 0) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.code = READER_ERROR_CODE


#: Diagnostic only, never control flow: how many read attempts the MOST RECENT
#: armed `analyze()` call made (1 = clean, 2 = one retry). Exists so the bar can
#: MEASURE that the retry happened instead of inferring it from a timing.
LAST_READ_ATTEMPTS: int = 0


def sb2_match_pill_accepts_label_map(sb2_match_pill: Optional[Callable[..., Any]]) -> bool:
    """`True` iff the (already-resolved) `sb2.match_pill` this process
    imported declares a `label_to_din` parameter -- the one signal this
    file uses to tell production `SB2/` apart from the promoted prototype,
    without hardcoding either path (module docstring)."""
    if sb2_match_pill is None:
        return False
    try:
        return "label_to_din" in inspect.signature(sb2_match_pill).parameters
    except (TypeError, ValueError):
        return False


def build_verify_session(dins: list, *, allowlist_csv: Path = ALLOWLIST_CSV,
                          reference_workbook: Any) -> Any:
    """Best-effort construction. Returns `None` on ANY failure -- never
    raises -- see the module docstring for the two independent, MEASURED
    ways this fails against production `SB2/`."""
    if VerifySession is None or reference_workbook is None:
        return None
    try:
        return VerifySession(profile_dins=dins, allowlist_csv=allowlist_csv,
                              reference_workbook=reference_workbook)
    except Exception:
        return None


def decide(record: dict, dins: list, *, sb2_match_pill: Callable[..., Any],
           reference_workbook: Any, session: Any = None) -> dict:
    """The STEP 7b call site. Replaces the bare
    `sb2_match_pill(record, dins)` call `app.py`'s `/pill/analyze` made
    before this step (the standing `PRODUCTION_WIRING: OWED` condition --
    see `harness/NB08_C6/mutate_c6_adapter.py`'s `d8_deployed_config_check`).

    `sb2_match_pill` and `reference_workbook` are INJECTED by the caller
    (app.py's own `_sb2_match_pill` / `sb2_reference._DEFAULT_XLSX`) rather
    than imported here, so this module never imports `sb2`/`imb1`/`fastapi`
    itself -- see the module docstring for why, and
    `harness/NB08_C6/test_production_wiring.py` for the bars this shape was
    written to satisfy.

    Builds a session from THIS call's OWN `dins` (the lexicon must reflect
    the patient in front of the camera -- `nb08_lexicon.build_lexicon`'s own
    docstring), then calls `VerifySession.decide(record)`, which asserts
    every face's `read['lexicon_id']` against this session's OWN lexicon
    BEFORE calling `sb2.match_pill(record, dins, label_to_din=...)` --
    never a hand-built map, never `.surface` (open item 14's foreclosed
    route -- `VerifySession.label_to_din` already enforces this; see that
    property's own docstring).

    M1 (2026-08-14): `session` may be supplied by `analyze()`, which has
    ALREADY built one to give the reader its ballot. When it is, that SAME
    session decides -- rebuilding one here would defeat PROV-1 (`nb08_verify
    .py:176`), whose whole job is to prove the ballot that produced a read and
    the map that resolves it are the same `Lexicon` INSTANCE. Two sessions
    built from identical inputs would currently pass the id check and would
    stop passing it the moment they ever diverged, which is precisely when the
    check is supposed to fire.
    """
    global LAST_DECISION_SOURCE
    if session is not None:
        LAST_DECISION_SOURCE = "wired_session"
        return session.decide(record)
    if sb2_match_pill_accepts_label_map(sb2_match_pill):
        vs = build_verify_session(dins, reference_workbook=reference_workbook)
        if vs is not None:
            LAST_DECISION_SOURCE = "wired"
            return vs.decide(record)
        LAST_DECISION_SOURCE = "fallback_construction_failed"
    else:
        LAST_DECISION_SOURCE = "fallback_no_label_kwarg"
    return sb2_match_pill(record, dins)


# ===========================================================================
# M1 (2026-08-14) -- the READER path: `/pill/analyze` produces a C6 record
# ===========================================================================
#
# STEP 7b made the `label_to_din` map REACHABLE. It was still not EFFECTIVE:
# `imb1.analyze_pill()` returns the legacy record shape, `sb2.match_pill`
# branches on `record["contract_version"] == "C6"`, and a legacy record never
# reaches that branch -- so the map was accepted and ignored on every real
# photo. This section is what finally produces a C6 record from a photograph.
#
# THE SINGLE-MODEL DECISION. Stage 2 (`ConstrainedScorer`) already loads
# `Qwen/Qwen3-VL-4B-Instruct` 4-bit NF4 in-process. NB08_37 measured those SAME
# weights at Stage 1 (free generation with the A3 prompt) as ~20x faster than
# the 8.8B Ollama incumbent while passing the safety bars. So Stage 1 becomes
# `scorer.generate_presence` -- one model, both stages, one 4-bit copy in an
# 8.6 GB card, and no eviction between the stages.
#
# 🔴 A LATENT BUG THIS AVOIDS RATHER THAN FIXES (out of scope, do not "fix"
# here): `nb08_arbiter.TransformersHandle._unload` clears only `handle.obj`, so
# a reader holding a strong reference to the scorer would keep the weights
# resident across an eviction the arbiter believes it performed. The
# single-model path never evicts, so it never trips this. It remains a real
# bug on the two-model path and is filed, not closed.

#: Populated when the Stage 2 scorer fails to load. Read by `/health`-style
#: reporting and by `reader_backend_report()`; never used as control flow.
SCORER_LOAD_ERROR: Optional[str] = None

_SCORER: Any = None

#: The rendering the crops are written in and the gate was fitted on.
M0_RENDERING = "M0"

#: The PREREG's 2-decimal figures, verbatim from
#: `harness/NB08_C6/repro_sample17.py:85`. These are NOT the thresholds --
#: `frozen_threshold()` returns the exact float and gating at a rounded number
#: re-admits the wrong pick the freeze existed to exclude. They are the
#: PROVENANCE ASSERTION: supplied by the caller so `nb08_reader` needs no
#: literal of its own, and any drift in the TRAIN workbook stops the run.
FILED_2DP = {"M0": 8.59, "M0raw": 12.11, "M1": 8.15, "M2": 9.15}


def get_scorer(device: Optional[str] = None) -> Any:
    """The ONE `ConstrainedScorer` for this process, loaded on first use.

    A per-request scorer would reload ~2.5 GB of 4-bit weights per photo and
    would race itself on an 8.6 GB card. Loaded LAZILY rather than at import so
    that a sidecar started with the reader switched off never touches the GPU,
    and so an import of this module stays cheap for the bars that do not need a
    model (`harness/NB08_C6/test_production_wiring.py` runs on plain python).
    """
    global _SCORER, SCORER_LOAD_ERROR
    if _SCORER is None:
        import config                                    # noqa: PLC0415
        from nb08_constrained_score import ConstrainedScorer  # noqa: PLC0415
        try:
            _SCORER = ConstrainedScorer(device=device or config.SCORER_DEVICE)
            SCORER_LOAD_ERROR = None
        except Exception as exc:
            SCORER_LOAD_ERROR = repr(exc)
            raise
    return _SCORER


def build_reader(session: Any, *, scorer: Any = None, stage1: Optional[str] = None,
                 threshold: Optional[float] = None) -> Any:
    """`session.reader(...)` with Stage 1 and Stage 2 chosen by config.

    Built through `VerifySession.reader()` -- NEVER `TwoStageReader(...)`
    directly -- because that method is what guarantees the reader's ballot is
    the session's OWN `Lexicon` object, which is the whole basis of PROV-1.

    STAGE 1 = "single" (default): `scorer.generate_presence`, the same loaded
    weights Stage 2 uses. `a3_model` is set EQUAL to `a4c_model` on purpose: if
    an arbiter is ever supplied, `TwoStageReader._call_a3`'s same-name lookup
    makes Stage 1's `acquire()` a no-op instead of asking the arbiter to evict
    and reload the model it is about to use again one line later.

    STAGE 1 = "ollama": `a3` is left None, so `TwoStageReader._call_a3` falls
    back to `nb08_read16_vlm.call_a3` (8.8B over HTTP), and `a3_model` stays
    DISTINCT from `a4c_model` -- two real models, which an arbiter must
    actually arbitrate.

    🔴 WHAT `ollama` IS NOT -- CORRECTED 2026-08-14 (REPAIR agent, finding S6).
    It is a fallback for STAGE 1 ONLY. Read the line below: it still evaluates
    `scorer or get_scorer()`, because Stage 2 (`score_crop`) is the constrained
    ranker and there is no Ollama substitute for it. So `PILLSAFE_STAGE1=ollama`
    still loads the 4-bit NF4 scorer and still needs `bitsandbytes` +
    `accelerate` + a GPU. It is NOT a deps-free path and must never be offered
    as the answer to a Stage 2 load failure. The ONLY switch that avoids the
    scorer entirely is `PILLSAFE_READER=off`, which skips this function.
    (The ollama branch is deliberately NOT redesigned here; the promise is
    corrected to match the code, not the code bent to match the promise.)
    """
    import config                                        # noqa: PLC0415
    from nb08_reader import frozen_threshold             # noqa: PLC0415

    stage1 = (stage1 or config.STAGE1_BACKEND).strip().lower()
    if threshold is None:
        # RECOMPUTED from the Sample16 TRAIN workbook on every call (D17-4) --
        # a remembered threshold is not a frozen one. The arm is the RENDERING
        # arm ("M0"), NOT an arm name like "A4c": measured 2026-08-14, passing
        # "A4c" raises `KeyError ... workbook has ['M0','M0raw','M1',...]`, and
        # `FILED_2DP` below is the same provenance assertion
        # `harness/NB08_C6/repro_sample17.py:85` files. If the workbook ever
        # changes so that M0 stops rounding to 8.59, this RAISES rather than
        # quietly gating a patient's photo at a different bar.
        threshold = frozen_threshold(M0_RENDERING, filed_2dp=FILED_2DP)

    if stage1 == "ollama":
        return session.reader(
            threshold=threshold, rendering="M0", scorer=scorer or get_scorer(),
            a3=None, a3_model="A3", a4c_model="A4c",
            presence_source="A3:qwen3-vl:latest")

    sc = scorer or get_scorer()
    from nb08_constrained_score import MODEL_ID          # noqa: PLC0415
    return session.reader(
        threshold=threshold, rendering="M0", scorer=sc,
        a3=sc.generate_presence, a3_model="A4c", a4c_model="A4c",
        presence_source=f"A3:{MODEL_ID}:nf4")


def reader_backend_report() -> dict:
    """What this process WOULD do, without doing it -- for `/health` and for a
    bar that needs to check configuration without loading a 4-bit model."""
    import config                                        # noqa: PLC0415
    return {
        "reader_enabled": bool(config.READER_ENABLED),
        "reader_mode": config.READER_MODE,
        "stage1_backend": config.STAGE1_BACKEND,
        "scorer_device": config.SCORER_DEVICE,
        "scorer_loaded": _SCORER is not None,
        "scorer_load_error": SCORER_LOAD_ERROR,
        "verify_session_import_error": VERIFY_SESSION_IMPORT_ERROR,
    }


def analyze(photo, profile_dins: list, *, reference_workbook: Any,
            scorer: Any = None, crop_dir: Any = None) -> tuple:
    """`(record, session)` -- a C6 record read against THIS patient's ballot.

    THE SESSION IS HOISTED, and that is the point of this function. Before M1,
    `decide()` built its `VerifySession` inside itself, after the record already
    existed -- which is too late for a reader that needs the ballot in order to
    read at all. Here ONE session is built first, its lexicon gives the reader
    its candidate set, and the SAME object is handed to `decide()` afterwards,
    so PROV-1's `lexicon_id` assertion compares a read against the very instance
    that produced it.

    Raises `ReaderError` when no session can be BUILT (a moved allowlist, an
    unreadable workbook, an `sb2` too old to take the map) -- GOAL1 (2026-08-15),
    re-landed 2026-08-18: this used to return `(record, None)` from the legacy
    `imb1.analyze_pill()` appearance-only path, so the caller still had an
    answer even though it was unarmed. That legacy path is gone; the two-stage
    reader is the ONLY arm (owner decision 2026-08-15, reaffirmed 2026-08-18),
    so a session that cannot be built is now the SAME refusal as an armed read
    that fails -- see `ReaderError` for why this is a refusal, never a silent
    fallback.

    🔴 CONFIGURATION AND EXECUTION ARE NOT THE SAME FAILURE, and this docstring
    used to blur them (corrected 2026-08-14, REPAIR agent, finding S7). Only
    session construction was ever guarded. Once the reader is armed and
    RUNNING, an exception from Stage 1/2 -- a CUDA OOM under a second
    concurrent request, a decode failure -- propagated straight out of here
    into `app.py`'s blanket `except Exception`, which returned 422
    `PILL_ANALYSIS_FAILED`: the same code it returns for "no pill in this
    photo", on a request the OFF deployment would have answered. That is now
    explicit rather than accidental: ONE retry (a transient OOM usually clears
    once the other request's tensors are freed), then a typed `ReaderError`
    that `app.py` maps to a 422 carrying `READER_ERROR_RETRYABLE`. Still a
    refusal -- see `ReaderError` for why it must NOT silently fall back to the
    legacy PaddleOCR reader -- but a refusal that names its own cause.

    The retry is UNCONDITIONAL on exception type, deliberately: the exceptions
    that reach here (`torch.OutOfMemoryError`, decode errors, a driver hiccup)
    are not reliably distinguishable from deterministic ones by class, and the
    cost of being wrong is bounded at one extra attempt on a request that has
    already failed. It re-runs the WHOLE `analyze_pill` (appearance heads
    included), because the reader is invoked from inside it and there is no
    seam that re-enters at just the read.
    """
    import nb08_imb1                                     # noqa: PLC0415

    global LAST_READ_ATTEMPTS
    dins = [str(d) for d in profile_dins]
    session = build_verify_session(dins, reference_workbook=reference_workbook)
    if session is None:
        LAST_READ_ATTEMPTS = 0
        # GOAL1 (2026-08-15), re-landed 2026-08-18: a session-build failure
        # used to fall back to the legacy
        # `imb1.analyze_pill(photo, profile_dins=dins)` appearance-only path
        # (removed -- see
        # `archive\2bdeleted\2026-08-15_paddleocr_removal\MANIFEST.md`).
        # There is no second arm left to degrade to, so this is now the SAME
        # refusal `ReaderError` raises for an armed read that fails, not a
        # softer one -- consistent with the no-fallback stance in
        # `ReaderError`'s own docstring above.
        raise ReaderError(
            "could not build a VerifySession for this request -- the reader "
            "has no ballot to read against (a moved allowlist, an unreadable "
            "reference workbook, or an sb2 build too old to accept the map). "
            "Refused rather than answered from the legacy paddle OCR path, "
            "which was removed 2026-08-15 (retirement re-landed 2026-08-18).",
            attempts=0,
        )

    reader = build_reader(session, scorer=scorer)
    attempts, last_exc = 0, None
    for attempts in (1, 2):
        try:
            record = nb08_imb1.analyze_pill(photo, profile_dins=dins,
                                            reader=reader, crop_dir=crop_dir)
            LAST_READ_ATTEMPTS = attempts
            return record, session
        except Exception as exc:                         # noqa: BLE001
            last_exc = exc
            if attempts == 1:
                _free_vram_best_effort()
                continue
    LAST_READ_ATTEMPTS = attempts
    raise ReaderError(
        f"the armed two-stage reader failed on this request after {attempts} "
        f"attempts: {type(last_exc).__name__}: {last_exc}", attempts=attempts
    ) from last_exc


def _free_vram_best_effort() -> None:
    """Between the two attempts only. Silent on every failure BY DESIGN -- this
    is a courtesy to the retry, never a step it depends on, and a sidecar
    running on CPU (`PILLSAFE_SCORER_DEVICE=cpu`) has no cache to empty."""
    try:
        import torch                                     # noqa: PLC0415
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:                                    # noqa: BLE001, S110
        pass
