# ---------------------------------------------------------------------------
# PROMOTED COPY -- DO NOT EDIT HERE, AND DO NOT EDIT THE ORIGINAL.
#
#   source : D:\Projects\PillSafe\IMB1_Prototype\NB08_Notebook\src\nb08_messages.py
#   copied : 2026-08-14 (MPR1-T04-BLD)
#   sha256 : d276d1363fb774e905c41979e85d0e375b9a140d7324fd17ffca9497af24f177   (of the SOURCE file, byte-for-byte identical below)
#
# This is an ADDITIVE promotion of the NB08 prototype module into the backend.
# The prototype original is the system of record; if it changes, re-copy and
# update the sha256 above. Backend-specific behaviour belongs in
# app/services/tray_messages.py, never in this file.
# ---------------------------------------------------------------------------
"""C.6 -- the three UI messages.  A pure function over a C6 record.

WHY THIS IS A SEPARATE, DETERMINISTIC LAYER
-------------------------------------------
Build spec section 6 names three states and warns that collapsing any two of
them "kills the value of the gate that produces them".  They are three
different USER ACTIONS:

    UNREADABLE   -> try again, or turn the pill over        RECOVERABLE
    NONE         -> MyPillSafe cannot identify this pill    TERMINAL (v3 1.8)
    unsupported  -> this medication is not covered yet      SCOPE LIMIT (C8)

Those are not three shades of "sorry".  Section 3.16 measured that Stage 1
expresses a distinction Stage 2 structurally cannot -- the margin gate collapses
"no imprint" and "an imprint I cannot resolve" into one abstain, and v3 1.8
routes them oppositely -- and section 3.17 confirmed it out of sample.  One
message for all three throws that away at the last inch.

LANGUAGE
--------
Every message is a KEY plus PARAMS plus English fallback copy.  Translation
happens downstream (CB4 is the only brain that speaks the user's language).
This layer stays deterministic, local and language-free: no cloud key ever
reaches SB2 or IMB1, and a user whose device is offline still gets correct
routing, just in English.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not emit SB2's reference-aware flip prompt.  That is C3, it lives in the
matcher, it requires the ordered sides from the reference, and v3 1.3.1
SUPPRESSES it when the two sides carry the same text.  This module only reports
how many faces were photographed and lets the app decide; conflating the two
would put a reference-dependent decision in a layer that has never seen the
reference.

Copy is 🟡 UNVALIDATED for the target population (seniors, people with language
barriers).  No citation supports this wording.  It is defensible plain English,
not evidence-based copy, and it should be user-tested before launch.

ASCII ONLY.  The cp1252 console trap has fired four times in this project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


class MsgKey:
    """The closed set.  A key not in ALL is a bug, not a new message."""

    UNREADABLE = "pill.presence.unreadable"
    NO_IMPRINT = "pill.presence.none"
    UNSUPPORTED = "pill.scope.unsupported"
    UNSUPPORTED_NOTE = "pill.scope.unsupported_note"
    NO_PROFILE = "pill.scope.no_profile"

    ALL = frozenset({UNREADABLE, NO_IMPRINT, UNSUPPORTED, UNSUPPORTED_NOTE,
                     NO_PROFILE})


@dataclass(frozen=True)
class Message:
    key: str
    params: Dict[str, Any] = field(default_factory=dict)
    default_en: str = ""


@dataclass(frozen=True)
class MessageSet:
    """`primary` is None when this layer has nothing to say.

    That happens on exactly one path: an imprint was read and cleared the margin
    gate, so the pill is identifiable and SB2's decision owns the user-facing
    result.  Returning an empty set there is deliberate -- a scope layer that
    also narrates successes will eventually narrate over a verification.
    """

    primary: Optional[Message]
    notes: Tuple[Message, ...] = ()
    terminal: bool = False


@dataclass(frozen=True)
class ScopeRow:
    din: str
    product_key: Optional[str]
    supported: bool


# --------------------------------------------------------------------------
# English fallback copy.  Short sentences, one idea each, no clinical verbs.
# --------------------------------------------------------------------------
_EN = {
    MsgKey.UNREADABLE:
        "We could not read the markings on this pill. "
        "Try another photo, or turn the pill over and photograph the other side.",
    MsgKey.NO_IMPRINT:
        "This pill has no markings, so MyPillSafe cannot identify it. "
        "Please check with your pharmacist.",
    MsgKey.UNSUPPORTED:
        "MyPillSafe does not cover any of the medications on your list yet, "
        "so it cannot check this pill.",
    MsgKey.UNSUPPORTED_NOTE:
        "Some of the medications on your list are not covered by MyPillSafe yet. "
        "This pill might be one of them.",
    MsgKey.NO_PROFILE:
        "There are no medications on your list yet, so there is nothing to "
        "check this pill against.",
}


def profile_scope(*, profile_dins: Iterable[str],
                  allowlist) -> List[ScopeRow]:
    """Profile-screen view: which enrolled medications can actually be checked.

    Naming the medication IS correct here -- it is the user's own list and no
    photograph is in play.  Contrast the photo-time note below, which must stay
    anonymous.  Build spec 4.2: an unsupported member must never be silently
    dropped, and this is the honest place to say so, before the user is standing
    over a pill wondering why nothing happened.
    """
    rows: List[ScopeRow] = []
    for d in profile_dins:
        supported = allowlist.is_supported(d)
        rows.append(ScopeRow(din=d, product_key=allowlist.product_key(d),
                             supported=supported))
    return rows


def resolve(record, *, profile_dins: Iterable[str], allowlist) -> MessageSet:
    """Map a C6 record plus the patient's profile onto at most one primary
    message and zero or more notes.

    PRECEDENCE, settled with Muthu 2026-08-11: the presence verdict wins the
    primary slot because it describes THE OBJECT THE USER JUST PHOTOGRAPHED;
    scope is a property of their list, so it rides along as a note.  The one
    exception is a profile where nothing at all is covered -- then no photograph
    of anything can succeed, and saying "try again" would be a lie.
    """
    profile = list(profile_dins)
    if not profile:
        return MessageSet(primary=_msg(MsgKey.NO_PROFILE, profile_n=0),
                          terminal=True)

    unsupported = allowlist.unsupported(profile)
    counts = {"unsupported_n": len(unsupported), "profile_n": len(profile)}

    # Nothing on the list is covered: a retry cannot help, so this is terminal
    # and it takes the primary slot rather than riding as a note.
    if len(unsupported) == len(profile):
        return MessageSet(primary=_msg(MsgKey.UNSUPPORTED, **counts), terminal=True)

    notes: Tuple[Message, ...] = ()
    if unsupported:
        # ANONYMOUS BY CONSTRUCTION -- counts only, never a product key.  We do
        # not know which pill this is; that is why we are abstaining.  Naming a
        # medication next to an abstain reads as an identification the system
        # has not made, which is a wrong-drug suggestion by implication.
        notes = (_msg(MsgKey.UNSUPPORTED_NOTE, **counts),)

    # An identification succeeded -- this layer stays quiet and lets SB2 speak.
    if record.has_imprint_evidence():
        return MessageSet(primary=None, notes=notes, terminal=False)

    faces_seen = len(record.faces)

    # v3 1.8, TERMINAL.  `is_out_of_scope` already requires EVERY photographed
    # face to be imprint-free: modality is a property of the face, not of the
    # product, so one blank face proves nothing on its own.
    if record.is_out_of_scope():
        return MessageSet(primary=_msg(MsgKey.NO_IMPRINT, faces_seen=faces_seen),
                          notes=notes, terminal=True)

    # Everything else is recoverable: unreadable, gated below the margin
    # threshold, or no pill found in the frame at all.
    return MessageSet(primary=_msg(MsgKey.UNREADABLE, faces_seen=faces_seen,
                                   unseen_face_possible=faces_seen < 2),
                      notes=notes, terminal=False)


def _msg(key: str, **params: Any) -> Message:
    if key not in MsgKey.ALL:
        raise ValueError(f"undeclared message key {key!r}")
    return Message(key=key, params=params, default_en=_EN[key])
