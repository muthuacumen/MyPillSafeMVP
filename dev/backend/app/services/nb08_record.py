# ---------------------------------------------------------------------------
# PROMOTED COPY -- DO NOT EDIT HERE, AND DO NOT EDIT THE ORIGINAL.
#
#   source : D:\Projects\PillSafe\IMB1_Prototype\NB08_Notebook\src\nb08_record.py
#   copied : 2026-08-14 (MPR1-T04-BLD)
#   sha256 : a01b2edb6d41b8f6a1de114910db4d6ff2e475efba2587f4a7d2e2d2b346abd4   (of the SOURCE file, byte-for-byte identical below)
#
# This is an ADDITIVE promotion of the NB08 prototype module into the backend.
# The prototype original is the system of record; if it changes, re-copy and
# update the sha256 above. Backend-specific behaviour belongs in
# app/services/tray_messages.py, never in this file.
# ---------------------------------------------------------------------------
"""NB08 -- the C6 IMB1 record, and the C7 two-list guard.

Build spec: specs/NB08_C6_Contract_Build.md sections 2 and 3.

WHAT CHANGED, AND WHY
---------------------
The shipped record (IMB1_v0/CONTRACT.md:38-60) carries:

    "imprint_reads": {"i1": "APO 200", "i3": "APO 200"}

-- two reads of the SAME face by two preprocessing paths.  It cannot express which
face was photographed (C1), whether an imprint is present at all (v3 section 1.8),
or how confident the read is in the only sense that carries safety (A4c's margin).
All three are required by the two-stage reader.

THE DESIGN RULE THIS MODULE ENFORCES
------------------------------------
The safe reading must be the EASY reading.  Two mechanisms in the record are load
bearing and both are easy to bypass by accident:

  * `presence` separates "no imprint" (terminal, out of scope) from "an imprint I
    could not resolve" (recoverable, reshoot or flip).  v3 section 1.8 routes them
    OPPOSITELY.  It is CONSUMED from A3's Stage 1, never inferred from whether the
    read came back empty -- section 3.16 measured that a reader without a presence
    gate cannot tell those apart.

  * `gated` says the PMI margin fell below the frozen threshold.  The margin gate is
    what zeroes fabrication on all seven arms.  A consumer that reads `top1` while
    ignoring `gated` REMOVES THE ENTIRE SAFETY MECHANISM.

So `top1` is never the obvious accessor.  `FaceRecord.usable_text()` is, and it
returns None unless presence is TEXT and the read is ungated.  Reaching the raw
string requires asking for it by a name that says what you are doing.

NOTE ON CONSOLE OUTPUT: ASCII only.  The cp1252 print trap has recurred three times.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "CONTRACT_VERSION",
    "Presence",
    "ContractError",
    "ProfileMismatch",
    "ImprintRead",
    "FaceRecord",
    "PillRecord",
    "validate_record",
    "assert_same_profile",
]

CONTRACT_VERSION = "C6"


class Presence:
    """A3's Stage 1 three-way verdict.  Not an enum, so it survives JSON round-trips
    without a codec, but the legal set is closed and validated."""

    TEXT = "TEXT"          # an imprint is present and was resolvable -> Stage 2 ran
    UNREADABLE = "UNREADABLE"  # an imprint is present, not resolvable -> RECOVERABLE: reshoot or flip
    NONE = "NONE"          # no imprint on this face -> TERMINAL under v3 section 1.8

    ALL = frozenset({TEXT, UNREADABLE, NONE})


class ContractError(ValueError):
    """A record violated the C6 contract.  Always raised, never warned -- a record
    that is wrong in these fields is worse than no record."""


class ProfileMismatch(ContractError):
    """C7 section 3.2 -- IMB1's lexicon profile and SB2's scoring profile disagree.

    NOTE: `sb2.ProfileMismatch` states the same rule on the other side of the package
    boundary (SB2 is standalone and cannot import this module).  It is a DIFFERENT
    CLASS with the same name -- catching one does not catch the other.  Both subclass
    ValueError so that code spanning the boundary can catch `ValueError` and mean it.
    Bars C6g3/C6g4 and D1 in harness/NB08_C6/test_c7_profile.py hold this true.
    """


# ------------------------------------------------------------------------------ reads


@dataclass
class ImprintRead:
    """Stage 2 (A4c).  Present ONLY when presence == TEXT."""

    top1: Optional[str]          # a lexicon entry, or None for "none of these"
    margin: float                # PMI margin -- the safety mechanism
    gated: bool                  # True => below the frozen threshold => treat as NO read
    threshold: float             # the frozen value ACTUALLY APPLIED, recorded per record
    lexicon_id: str              # which lexicon this was scored against
    arm: str = "A4c"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ImprintRead":
        missing = {"top1", "margin", "gated", "threshold", "lexicon_id"} - set(d)
        if missing:
            raise ContractError(f"read is missing required fields: {sorted(missing)}")
        return ImprintRead(
            top1=d["top1"],
            margin=float(d["margin"]),
            gated=bool(d["gated"]),
            threshold=float(d["threshold"]),
            lexicon_id=str(d["lexicon_id"]),
            arm=str(d.get("arm", "A4c")),
        )


@dataclass
class FaceRecord:
    """One face ACTUALLY PHOTOGRAPHED.

    `face_id` is OPAQUE by design.  IMB1 cannot know whether it saw side1 or side2 --
    that mapping is the reference's business, resolved inside SB2 against C5's ordered
    sides (v3 section 1.3).  Writing side1/side2 here re-creates exactly the conflation
    v3 section 1.3 was written to remove, so it is rejected by the validator.
    """

    face_id: str
    presence: str
    presence_source: str
    rendering: str = "M0"
    read: Optional[ImprintRead] = None

    #: face_id values that assert knowledge IMB1 does not have
    FORBIDDEN_IDS = frozenset({"side1", "side2", "side_1", "side_2", "s1", "s2"})

    # -- the accessors ---------------------------------------------------------

    def usable_text(self) -> Optional[str]:
        """The ONLY safe way to get an imprint string out of a face.

        Returns None unless Stage 1 said TEXT and Stage 2's margin cleared the frozen
        threshold.  Everything else -- no imprint, unreadable, gated, 'none of these' --
        yields None, because downstream they all mean the same thing: no imprint
        evidence from this face.
        """
        if self.presence != Presence.TEXT or self.read is None or self.read.gated:
            return None
        return self.read.top1

    def raw_top1(self) -> Optional[str]:
        """The ungated string, for diagnostics and eval ONLY.

        Named so that using it is a visible decision.  Never feed this to the matcher.
        """
        return None if self.read is None else self.read.top1

    def is_terminal_no_imprint(self) -> bool:
        """v3 section 1.8 -- out of scope, a TERMINAL state.  Distinct from unreadable."""
        return self.presence == Presence.NONE

    def is_recoverable(self) -> bool:
        """Reshoot or flip will plausibly help.  A DIFFERENT user action from terminal."""
        return self.presence == Presence.UNREADABLE or (
            self.presence == Presence.TEXT and self.read is not None and self.read.gated
        )

    # -- serialisation ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "face_id": self.face_id,
            "rendering": self.rendering,
            "presence": self.presence,
            "presence_source": self.presence_source,
        }
        if self.read is not None:
            d["read"] = self.read.to_dict()
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FaceRecord":
        return FaceRecord(
            face_id=str(d["face_id"]),
            presence=str(d["presence"]),
            presence_source=str(d.get("presence_source", "")),
            rendering=str(d.get("rendering", "M0")),
            read=ImprintRead.from_dict(d["read"]) if "read" in d else None,
        )


@dataclass
class PillRecord:
    """The C6 record.  Appearance-head semantics are unchanged (v3 1.4 / 1.7)."""

    detected: bool
    photo: str
    colour_modes: List[Dict[str, Any]] = field(default_factory=list)
    shape_out: Optional[str] = None
    shape_conf: Optional[float] = None
    type_out: Optional[str] = None
    type_conf: Optional[float] = None
    faces: List[FaceRecord] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    #: the profile IMB1 built its lexicon from -- C7.  Carried so SB2 can check.
    lexicon_profile_dins: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    # -- the accessors ---------------------------------------------------------

    def usable_reads(self) -> List[str]:
        """Every safe imprint string across the photographed faces."""
        return [t for t in (f.usable_text() for f in self.faces) if t]

    def has_imprint_evidence(self) -> bool:
        return bool(self.usable_reads())

    def is_out_of_scope(self) -> bool:
        """v3 section 1.8 -- TERMINAL.  True only when every photographed face is
        genuinely imprint-free.  One unreadable face makes this False, because a
        reshoot could still resolve it."""
        return bool(self.faces) and all(f.is_terminal_no_imprint() for f in self.faces)

    # -- serialisation ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "photo": self.photo,
            "contract_version": self.contract_version,
            "colour_modes": self.colour_modes,
            "shape_out": self.shape_out,
            "shape_conf": self.shape_conf,
            "type_out": self.type_out,
            "type_conf": self.type_conf,
            "faces": [f.to_dict() for f in self.faces],
            "lexicon_profile_dins": list(self.lexicon_profile_dins),
            **({"diagnostics": self.diagnostics} if self.diagnostics else {}),
        }

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), **kw)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PillRecord":
        return PillRecord(
            detected=bool(d["detected"]),
            photo=str(d.get("photo", "")),
            colour_modes=list(d.get("colour_modes", [])),
            shape_out=d.get("shape_out"),
            shape_conf=d.get("shape_conf"),
            type_out=d.get("type_out"),
            type_conf=d.get("type_conf"),
            faces=[FaceRecord.from_dict(f) for f in d.get("faces", [])],
            contract_version=str(d.get("contract_version", "")),
            lexicon_profile_dins=list(d.get("lexicon_profile_dins", [])),
            diagnostics=dict(d.get("diagnostics", {})),
        )


# --------------------------------------------------------------------------- validate


def validate_record(rec: PillRecord | Dict[str, Any]) -> PillRecord:
    """Enforce every C6 section 2.4 rule.  Raises ContractError, never warns."""
    if isinstance(rec, dict):
        rec = PillRecord.from_dict(rec)

    if rec.contract_version != CONTRACT_VERSION:
        raise ContractError(
            f"contract_version is {rec.contract_version!r}, expected {CONTRACT_VERSION!r} "
            "-- refuse a record you do not understand rather than mis-read it"
        )

    if not rec.detected:
        if rec.faces:
            raise ContractError("detected=False but faces are present")
        return rec

    seen = set()
    for f in rec.faces:
        if f.face_id in seen:
            raise ContractError(f"duplicate face_id {f.face_id!r}")
        seen.add(f.face_id)

        if f.face_id.lower() in FaceRecord.FORBIDDEN_IDS:
            raise ContractError(
                f"face_id {f.face_id!r} asserts knowledge IMB1 does not have. "
                "face_id is OPAQUE; side1/side2 is resolved in SB2 against the reference "
                "(v3 section 1.3)"
            )

        if f.presence not in Presence.ALL:
            raise ContractError(
                f"presence {f.presence!r} is not one of {sorted(Presence.ALL)}"
            )

        if not f.presence_source:
            raise ContractError(
                f"face {f.face_id!r} has no presence_source. presence is CONSUMED from "
                "Stage 1, never inferred -- an unsourced verdict is an inferred one"
            )

        if f.presence == Presence.TEXT and f.read is None:
            raise ContractError(
                f"face {f.face_id!r} says TEXT but carries no read -- Stage 2 must have run"
            )

        if f.presence != Presence.TEXT and f.read is not None:
            raise ContractError(
                f"face {f.face_id!r} has presence={f.presence} and a read. "
                "read must be ABSENT (not null-filled) so a consumer that forgets to check "
                "presence fails loudly instead of silently reading a blank"
            )

        if f.read is not None:
            # 🔴 CORRECTED 2026-08-11 (C.7). This read `margin < threshold`, which
            # contradicted the gate the frozen experiment actually applied:
            # run_sample17.py:224 gates with a STRICT `>`
            # (`match if margin > thr else "abstain_gated"`), i.e. equality is
            # GATED. D17-4 is the ruling behind that -- Muthu, 2026-08-10, before
            # TEST was touched: freeze at the EXACT zero-wrong point with a strict
            # `>`, because at the rounded `>= 8.59` the TRAIN data still admits one
            # wrong pick. The two rules differ only at margin == threshold, and the
            # old one differed IN THE UNSAFE DIRECTION: it admitted a read the
            # frozen experiment rejected. Measure-zero in floating point, and the
            # safety mechanism itself in meaning.
            #
            # C.1's 25/25 was recorded against the looser rule, and no bar caught
            # it -- a contract written after an experiment can restate that
            # experiment's rule wrongly while every bar still passes.
            gated_expected = not (f.read.margin > f.read.threshold)
            if f.read.gated != gated_expected:
                raise ContractError(
                    f"face {f.face_id!r}: gated={f.read.gated} disagrees with "
                    f"margin {f.read.margin} vs threshold {f.read.threshold} "
                    "under the frozen STRICT `>` gate (D17-4). "
                    "A frozen threshold that is re-derived downstream is not frozen"
                )
    return rec


# ------------------------------------------------------------------- C7 two-list guard


def assert_same_profile(
    record: PillRecord, sb2_profile_dins: Sequence[str], *, strict_order: bool = False
) -> None:
    """C7 section 3.2 -- the profile is consumed in TWO places now.

    If the list IMB1 built its lexicon from differs from the list SB2 scores against,
    the reader chose from candidates the matcher will not consider, and the failure is
    SILENT: it presents as an unexplained abstain.

    Fails LOUDLY.  Not a warning.  This is the same defect class as v3 section 4.1
    item 1 -- 'a field that only a human reads is decoration' -- which this project has
    now paid for three times (Sample16 face truth, the Sample19_C4 runners, and
    classify() branching on the truth label).
    """
    lex = list(record.lexicon_profile_dins)
    sb2 = list(sb2_profile_dins)

    if strict_order:
        if lex != sb2:
            raise ProfileMismatch(
                f"profile order differs: IMB1 lexicon {lex} vs SB2 {sb2}"
            )
        return

    if set(lex) != set(sb2):
        only_lex = sorted(set(lex) - set(sb2))
        only_sb2 = sorted(set(sb2) - set(lex))
        raise ProfileMismatch(
            "IMB1's lexicon profile and SB2's scoring profile disagree. "
            f"only in lexicon: {only_lex}; only in SB2: {only_sb2}. "
            "The reader chose from candidates the matcher will not consider"
        )
