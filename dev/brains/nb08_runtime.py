"""Bind the PROMOTED NB08 closure as a package -- WITHOUT putting it on sys.path.

MPR1-T30 (2026-08-20). Implements T29 section 4.3. ASCII ONLY -- the cp1252
console trap has recurred repeatedly in this project.

WHY THIS EXISTS
---------------
`production_wiring.py` used to make the closure importable by APPENDING
`NB08_SRC` to `sys.path`. Appending (never inserting) was correct and was
MEASURED: that directory contains `colour.py`, and the moment it outranks
site-packages the deferred `import colour as colour_science` in
`IMB1_v0/imb1/colour.py:277` binds to it, turning a working `analyze_pill()`
into `AttributeError: module 'colour' has no attribute 'CCS_ILLUMINANTS'` --
a defect that is invisible until a NON-NEUTRAL pill is actually measured.

But appending is ORDERING-dependent, and the project carries three independent
copies of that same repair (`production_wiring.py`, `nb08_verify.py`,
`nb08_tray_devserver.py`). Any future `sys.path.insert(0, SRC)` re-arms it, and
two modules in the closure itself already do an `insert(0, ...)` of a nearby
directory.

THE STRUCTURAL FIX
------------------
The promoted `src\\` directory NEVER goes on `sys.path`. Not appended, not
inserted, never. Instead it is bound as a PACKAGE under a private alias -- the
exact mechanism `nb08_tray.py:137-142` already uses, for the identical reason --
and only the explicitly enumerated `nb08_*` top-level names are aliased onto it.

`colour` is NOT in that set, and the directory is not on the path, so there is
no resolution order under which a bare `import colour` can reach
`<promoted>\\src\\colour.py`. The shadow is closed structurally, not defensively.
This rests on a measured fact (T29 section 4.2): `colour` is the ONLY
non-`nb08_*` module in the whole closure that is ever imported by an ABSOLUTE
bare name, and the only site doing so is `colour.py:384` importing the
third-party package it shadows. `src/colour.py` itself is reached exclusively by
RELATIVE import (`pipelines.py:33`), which resolves against `__package__`, not
`sys.path`, and therefore still works.

THE `src` ALIAS
---------------
Three modules carry an absolute `from src.<mod> import ...` spelling
(`nb08_constrained_score.py:308`, `nb08_presence.py:152`, `nb08_reader.py:192`).
Today `src` resolves against `config.py:178-180`'s `IMB1_ROOT` insert, i.e. to
the STALE ORPHANED `Production\\IMB1_v0\\src\\` copies, which must never be
reactivated. Binding `sys.modules["src"]` to the promoted package closes that
race by construction: `src.nb08_read16_vlm is nb08_read16_vlm` -- one copy, one
identity, no second instrument.

ONE MODULE OBJECT PER FILE (T29 open risk #1)
---------------------------------------------
`nb08_tray.py` binds the same directory under its OWN alias
`_nb08_tray_srcpkg`. Two package names over one directory would ordinarily
produce TWO module objects per file -- two copies of the frozen pipeline, two
sets of module globals, and a `FASTSAM_WEIGHTS` rebind that lands on only one of
them. So this module CANONICALISES: every alias spelling
(`_nb08_tray_srcpkg.X`, `src.X`, bare `nb08_X`) is loaded through a meta_path
finder that returns the module already bound as `_nb08_runtime.X`. Identity, not
equality. `check_identity()` below asserts it and is called by the T30/T31
verification.

Imports are LAZY: the finder resolves a name only when it is first imported, so
`import nb08_runtime` at sidecar start costs nothing and does not drag torch in.
"""
from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Dict, List, Optional

#: The canonical package name. Private so it can never collide with `src` --
#: the same ambiguity `nb08_tray.py:24-27` documents against `IMB1_v0\src\`.
PKG = "_nb08_runtime"

#: Alias package names bound to the SAME module object as `PKG`.
PKG_ALIASES = ("src", "_nb08_tray_srcpkg")

#: The ONLY top-level names aliased onto the promoted tree: the absolute-bare
#: set from T29 section 4.2 minus `colour`, plus the six entry points.
#: `colour` is deliberately absent -- that omission IS the fix.
ALIAS_NAMES = (
    "nb08_constrained_score", "nb08_geom", "nb08_geom10", "nb08_imb1",
    "nb08_lexicon", "nb08_outline", "nb08_paths", "nb08_pipe11",
    "nb08_presence", "nb08_read16", "nb08_read16_vlm", "nb08_reader",
    "nb08_record", "nb08_sections", "nb08_split", "nb08_tray",
    "nb08_verify", "nb08_verify11", "nb08_wells",
)


def _resolve_proto_root() -> tuple:
    """`(PROTO_ROOT, source)` -- env first, else derived from this file.

    This file lives at `<Production>\\PillSafe\\dev\\brains\\`, so `parents[3]`
    is `<Production>` -- the same sibling-of-repo convention
    `production_wiring.py:99` uses. No drive-lettered literal: a literal is
    exactly what makes a tree non-portable.
    """
    env = os.environ.get("PILLSAFE_PROTO_ROOT", "").strip()
    if env:
        return Path(env).resolve(), "env:PILLSAFE_PROTO_ROOT"
    return Path(__file__).resolve().parents[3] / "NB08_Runtime", "file:parents[3]"


def _resolve_src() -> tuple:
    """`(NB08_SRC, source)` -- `PILLSAFE_NB08_SRC` wins, else PROTO_ROOT-derived."""
    env = os.environ.get("PILLSAFE_NB08_SRC", "").strip()
    if env:
        return Path(env).resolve(), "env:PILLSAFE_NB08_SRC"
    proto, proto_source = _resolve_proto_root()
    return proto / "NB08_Notebook" / "src", f"{proto_source}/NB08_Notebook/src"


PROTO_ROOT, PROTO_ROOT_SOURCE = _resolve_proto_root()
NB08_SRC, NB08_SRC_SOURCE = _resolve_src()

# Fail loud at IMPORT time. A closure that cannot be located must stop the
# sidecar at startup, not surface as a per-well read failure mid-request.
if not (NB08_SRC.is_dir() and (NB08_SRC / "nb08_tray.py").is_file()):
    raise RuntimeError(
        f"PILLSAFE_NB08_SRC does not resolve to a promoted NB08 closure: "
        f"{NB08_SRC} (source: {NB08_SRC_SOURCE}; PROTO_ROOT={PROTO_ROOT} from "
        f"{PROTO_ROOT_SOURCE}). Expected a directory containing nb08_tray.py. "
        f"Set PILLSAFE_NB08_SRC, or PILLSAFE_PROTO_ROOT to a promoted "
        f"NB08_Runtime tree.")


def _canonical(fullname: str) -> Optional[str]:
    """The `PKG.X` name a given alias spelling must resolve to, or None."""
    if fullname in ALIAS_NAMES:
        return f"{PKG}.{fullname}"
    head, sep, tail = fullname.partition(".")
    if sep and head in PKG_ALIASES and tail:
        return f"{PKG}.{tail}"
    return None


class _AliasLoader:
    """Returns the ALREADY-bound canonical module. Never executes it twice."""

    def __init__(self, canonical: str) -> None:
        self.canonical = canonical

    def create_module(self, spec):                          # noqa: D102
        return importlib.import_module(self.canonical)

    def exec_module(self, module) -> None:                  # noqa: D102
        # Deliberately empty: `create_module` handed back a module the import
        # system already executed under its canonical name. Re-executing it is
        # precisely the second-copy defect this finder exists to prevent.
        return None


class _AliasFinder:
    """meta_path finder over an EXPLICIT name set -- never a wildcard."""

    def find_spec(self, fullname, path=None, target=None):   # noqa: D102
        canonical = _canonical(fullname)
        if canonical is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(canonical))


def _bind() -> types.ModuleType:
    """Install the package binding and the finder. Idempotent."""
    pkg = sys.modules.get(PKG)
    if pkg is None:
        pkg = types.ModuleType(PKG)
        pkg.__path__ = [str(NB08_SRC)]        # noqa: SLF001 - namespace by hand
        pkg.__package__ = PKG
        pkg.__spec__ = importlib.machinery.ModuleSpec(
            PKG, None, is_package=True)
        pkg.__spec__.submodule_search_locations = pkg.__path__
        sys.modules[PKG] = pkg
    else:
        pkg.__path__ = [str(NB08_SRC)]

    # Bind the alias package NAMES to the SAME object. `nb08_tray.py:138`'s
    # `if _PKG not in sys.modules` guard then reuses this one instead of
    # creating a second package over the same directory.
    for alias in PKG_ALIASES:
        existing = sys.modules.get(alias)
        if existing is not pkg:
            sys.modules[alias] = pkg

    if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
        # Position 0: the whole point is that resolution does not depend on
        # sys.path order.
        sys.meta_path.insert(0, _AliasFinder())
    return pkg


PACKAGE = _bind()

# The structural invariant, stated where it is easy to test. This module
# itself never puts NB08_SRC on sys.path -- see the docstring on the `colour`
# shadow. But a HARD assert here is wrong: T31 measured that every harness in
# this project (see `nb08_verify.py:97-99`'s own comment) appends the
# promoted src dir to sys.path BEFORE importing this module, which is
# PERMITTED (append, not insert -- `colour` still resolves to the real
# package first) and also vanishes under `python -O`. So this is RECORDED,
# not enforced, and surfaced via `report()`.
SRC_ON_SYS_PATH_AT_BIND: bool = str(NB08_SRC) in sys.path


def check_identity(names: Optional[List[str]] = None) -> Dict[str, str]:
    """T29 open risk #1: ONE module object per file, under every spelling.

    Imports each name under the bare alias, the canonical package name, the
    `src.` spelling and `nb08_tray.py`'s own `_nb08_tray_srcpkg.` spelling, and
    asserts all four are the SAME object. Raises `RuntimeError` on divergence.
    Returns `{name: __file__}` -- evidence, not assurance.
    """
    out: Dict[str, str] = {}
    for name in (names or list(ALIAS_NAMES)):
        bare = importlib.import_module(name)
        canon = importlib.import_module(f"{PKG}.{name}")
        via_src = importlib.import_module(f"src.{name}")
        via_tray = importlib.import_module(f"_nb08_tray_srcpkg.{name}")
        for label, mod in (("canonical", canon), ("src", via_src),
                           ("_nb08_tray_srcpkg", via_tray)):
            if mod is not bare:
                raise RuntimeError(
                    f"IDENTITY FAILURE for {name!r}: the {label} spelling is a "
                    f"DIFFERENT module object ({getattr(mod, '__file__', '?')} "
                    f"vs {getattr(bare, '__file__', '?')}). Two copies of one "
                    f"file is two instruments.")
        out[name] = str(getattr(bare, "__file__", "?"))
    return out


def report() -> Dict[str, object]:
    """Diagnostic snapshot for the T31/T32 closure audit. Loads nothing."""
    return {
        "PKG": PKG,
        "PROTO_ROOT": str(PROTO_ROOT),
        "PROTO_ROOT_SOURCE": PROTO_ROOT_SOURCE,
        "NB08_SRC": str(NB08_SRC),
        "NB08_SRC_SOURCE": NB08_SRC_SOURCE,
        "src_on_sys_path_at_bind": SRC_ON_SYS_PATH_AT_BIND,
        "alias_names": list(ALIAS_NAMES),
        "pkg_aliases": list(PKG_ALIASES),
        "finder_installed": any(isinstance(f, _AliasFinder) for f in sys.meta_path),
        "loaded": {n: str(getattr(sys.modules[n], "__file__", "?"))
                   for n in ALIAS_NAMES if n in sys.modules},
    }


__all__ = ["PKG", "PKG_ALIASES", "ALIAS_NAMES", "PROTO_ROOT", "PROTO_ROOT_SOURCE",
           "NB08_SRC", "NB08_SRC_SOURCE", "PACKAGE", "check_identity", "report"]
