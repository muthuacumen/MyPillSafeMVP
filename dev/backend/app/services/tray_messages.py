"""Tray slot verdicts -- the C.6 message vocabulary, per SLOT.

WHAT THIS LAYER IS
------------------
The sidecar returns six WELLS. The patient sees six SLOTS. This module turns
one well into one slot verdict: a stable verdict token, an alert level, ONE
user-facing message (key + params + English fallback), zero or more notes, and
the pharmacist hedge. It is a pure function of the sidecar's reply plus the
patient's profile -- no I/O, no database, no clock.

WHERE THE MESSAGES COME FROM
----------------------------
Presence and scope routing is DELEGATED, not re-implemented: it runs through
`nb08_messages.resolve`, the promoted C.6 module, so the precedence Muthu
settled on 2026-08-11 (the presence verdict owns the primary slot because it
describes the object photographed; scope rides along as a note) is honoured by
construction rather than by hand.

MUTHU'S THREE FILED TRAY CALLS (ADR 2026-08-14) LAND HERE
---------------------------------------------------------
(1) reader batching is the sidecar's business -- this module never batches;
(2) `slot = well + 1`, and each slot carries its own alert payload plus the
    pharmacist hedge (`slot_verdict` emits both on every slot, including the
    empty ones);
(3) in the TRAY flow, NONE routes to Flip/Reshoot ALONGSIDE Unreadable -- a
    deliberate deviation from the single-pill NONE-is-terminal semantics of
    v3 1.8. That deviation is `NoneRoute.RETRY`, the default.

STILL PENDING WITH MUTHU -- DO NOT DECIDE IT IN CODE
-----------------------------------------------------
Whether, and after how many attempts, the tray NONE/flip-reshoot loop becomes
terminal. A pill that is blank on BOTH faces would otherwise loop forever.
Both routes are built (`NoneRoute.RETRY` and `NoneRoute.TERMINAL`), the choice
is a request parameter the frontend binds later, and the default is RETRY.
Nothing in this module picks a winner.

PROVISIONAL MESSAGE KEYS
------------------------
`nb08_messages.MsgKey.ALL` is a CLOSED set covering presence and scope only --
by design, because on the identified path SB2's own decision owns the copy. A
tray grid has to say something in every cell, including "this well is empty",
"this well errored", and "this pill matched". Those keys do not exist in C.6.
They are declared below under the `tray.` namespace, every one of them marked
PROVISIONAL, and they are listed in the T04 report as a coverage gap. They are
plain-English ACTION copy, never clinical copy: no message here names a
medication, asserts an identity, or states a clinical fact.

ASCII only.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services import nb08_messages, nb08_record

logger = logging.getLogger(__name__)


class NoneRoute:
    """Muthu's call (3) plus the pending question. See module docstring."""

    RETRY = "retry"
    TERMINAL = "terminal"
    ALL = frozenset({RETRY, TERMINAL})
    DEFAULT = RETRY


class Verdict:
    """The closed set of per-slot verdicts the frontend switches on."""

    VERIFY = "verify"
    REJECT = "reject"
    ABSTAIN = "abstain"
    UNREADABLE = "unreadable"
    NO_IMPRINT = "no_imprint"
    EMPTY = "empty"
    ERROR = "error"
    READ_ONLY = "read_only"  # match was not requested (match=false)
    ALL = frozenset({VERIFY, REJECT, ABSTAIN, UNREADABLE, NO_IMPRINT, EMPTY, ERROR, READ_ONLY})


class Action:
    """What the user should DO. Distinct from the verdict on purpose: two
    verdicts can share an action (unreadable and tray-NONE both flip/reshoot)
    and collapsing them would undo the C.6 gate that produced them."""

    NONE = "none"
    FLIP_RESHOOT = "flip_reshoot"
    SHORTLIST = "shortlist"
    RETRY = "retry"
    ASK_PHARMACIST = "ask_pharmacist"


class Alert:
    OK = "ok"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


class TrayMsgKey:
    """PROVISIONAL keys. Every one of these is outside C.6's closed set and is
    reported as a coverage gap -- they must be reviewed before launch copy is
    frozen. Naming them here, rather than inlining English strings at the call
    site, is what makes the gap auditable."""

    VERIFY = "tray.slot.verify"
    REJECT = "tray.slot.reject"
    ABSTAIN = "tray.slot.abstain"
    ABSTAIN_ASK_TO_FLIP = "tray.slot.abstain.ask_to_flip"
    ABSTAIN_SHORTLIST = "tray.slot.abstain.shortlist"
    EMPTY = "tray.slot.empty"
    ERROR = "tray.slot.error"
    #: The gap that motivated Muthu's call (3): C.6 has no "no markings on this
    #: face -- turn it over" message, because in the single-pill flow NONE is
    #: terminal and never asks for anything. Reusing `pill.presence.unreadable`
    #: here would be a lie (we DID read the face; it is blank), and reusing
    #: `pill.presence.none` would print terminal copy under a retry action.
    NONE_RETRY = "tray.presence.none_retry"
    #: D-7. Distinct from ERROR on purpose: ERROR's copy says "try again",
    #: which would contradict the `ask_pharmacist` action D-7 requires. A
    #: record we cannot validate is not a transient camera problem.
    ERROR_CONTRACT = "tray.slot.error.contract"
    #: The single source of the per-slot hedge. The copy is SB2's shipped
    #: disclaimer, not new wording; the frozen match block carries no
    #: disclaimer of its own, so there is nothing to prefer over it.
    HEDGE = "tray.hedge.pharmacist"
    #: `match=false`: the pill was read but never scored against the profile.
    #: Without this the slot rendered a coloured badge and no copy at all --
    #: a cell the patient cannot read is a cell they will guess at.
    READ_ONLY = "tray.slot.read_only"

    PROVISIONAL = frozenset({
        VERIFY, REJECT, ABSTAIN, ABSTAIN_ASK_TO_FLIP, ABSTAIN_SHORTLIST,
        EMPTY, ERROR, NONE_RETRY, ERROR_CONTRACT, HEDGE, READ_ONLY,
    })
    ALL = PROVISIONAL


#: English fallback copy for the PROVISIONAL keys. Short sentences, one idea
#: each, no clinical verbs, no medication names. 🟡 UNVALIDATED for the target
#: population, exactly like the C.6 copy it sits beside.
_TRAY_EN = {
    TrayMsgKey.VERIFY:
        "This pill matches one of the medications on your list.",
    TrayMsgKey.REJECT:
        "This pill does not match any of the medications on your list. "
        "Do not take it. Check with your pharmacist.",
    TrayMsgKey.ABSTAIN:
        "MyPillSafe could not decide about this pill. Check with your pharmacist.",
    TrayMsgKey.ABSTAIN_ASK_TO_FLIP:
        "MyPillSafe needs to see the other side of this pill. "
        "Turn it over and photograph the tray again.",
    TrayMsgKey.ABSTAIN_SHORTLIST:
        "MyPillSafe narrowed this pill down but could not confirm one answer. "
        "Check with your pharmacist.",
    TrayMsgKey.EMPTY:
        "This slot is empty.",
    TrayMsgKey.ERROR:
        "MyPillSafe could not check this slot. Try photographing the tray again.",
    TrayMsgKey.ERROR_CONTRACT:
        "MyPillSafe could not check this slot safely, so it is not showing a result. "
        "Do not rely on this slot. Check with your pharmacist.",
    TrayMsgKey.NONE_RETRY:
        "There are no markings on the side of this pill that is facing up. "
        "Turn the pill over and photograph the tray again.",
    TrayMsgKey.HEDGE:
        "Decision-support only -- not a clinical determination. Verify with a pharmacist.",
    TrayMsgKey.READ_ONLY:
        "MyPillSafe did not check this pill against your medication list.",
}

#: The hedge Muthu's call (2) requires on every slot. Preferred source is the
#: sidecar's own `match.disclaimer`; this is the fallback.
DEFAULT_HEDGE = _TRAY_EN[TrayMsgKey.HEDGE]

SLOT_COUNT = 6


# --------------------------------------------------------------------------- msgs


def _tray_msg(key: str, **params: Any) -> Dict[str, Any]:
    if key not in TrayMsgKey.ALL:
        raise ValueError(f"undeclared tray message key {key!r}")
    return {"key": key, "params": params, "default_en": _TRAY_EN[key], "provisional": True}


def msg_to_dict(m: Optional[nb08_messages.Message]) -> Optional[Dict[str, Any]]:
    """A C.6 `Message` as JSON. `provisional` is False for every one of these --
    they come from the closed, reviewed set."""
    if m is None:
        return None
    return {"key": m.key, "params": dict(m.params), "default_en": m.default_en, "provisional": False}


# --------------------------------------------------------------------------- record


def record_view(record: Optional[Dict[str, Any]]) -> tuple[nb08_record.PillRecord, Optional[str]]:
    """Parse a sidecar `record` into the C6 `PillRecord` the message layer
    expects, plus a non-fatal contract complaint.

    LENIENT PARSE, LOUD REPORT. A record that is not C6-shaped (an older
    sidecar still emitting the shipped `imprint_reads` record, say) parses to
    zero faces, which routes to `pill.presence.unreadable` -- "try again" --
    the SAFE side of the fork, since with no faces we can prove nothing about
    markings. Raising instead would turn one bad well into a dead tray, and
    per-well failure isolation is the contract's whole point.

    The contract complaint is returned rather than swallowed: a validation
    error that only the log sees is decoration.
    """
    if not isinstance(record, dict) or "detected" not in record:
        return nb08_record.PillRecord(detected=False, photo=""), (
            None if record is None else "record: not a C6 record (missing 'detected')"
        )
    try:
        parsed = nb08_record.PillRecord.from_dict(record)
    except Exception as exc:  # noqa: BLE001 -- any parse failure is non-fatal here
        return nb08_record.PillRecord(detected=False, photo=""), f"record: unparseable ({exc})"

    contract_error: Optional[str] = None
    try:
        nb08_record.validate_record(record)
    except nb08_record.ContractError as exc:
        contract_error = f"record: {exc}"
        logger.warning("Tray well carried a record that fails C6 validation: %s", exc)
    except Exception as exc:  # noqa: BLE001
        contract_error = f"record: validation raised {exc}"
    return parsed, contract_error


# --------------------------------------------------------------------------- verdict


def _decision_slot(match: Dict[str, Any]) -> tuple[str, Dict[str, Any], str, str]:
    """SB2's decision owns the copy on the identified path. Verbatim: `verify`,
    `reject` and `abstain` are never reinterpreted or collapsed into each
    other (the same rule routes/scans.py already holds)."""
    outcome = match.get("outcome") or match.get("decision")
    abstain_action = match.get("abstain_action")
    if outcome == "verify":
        return Verdict.VERIFY, _tray_msg(TrayMsgKey.VERIFY), Action.NONE, Alert.OK
    if outcome == "reject":
        return Verdict.REJECT, _tray_msg(TrayMsgKey.REJECT), Action.ASK_PHARMACIST, Alert.DANGER
    if outcome == "abstain":
        if abstain_action == "ask_to_flip":
            return (Verdict.ABSTAIN, _tray_msg(TrayMsgKey.ABSTAIN_ASK_TO_FLIP),
                    Action.FLIP_RESHOOT, Alert.WARNING)
        if abstain_action == "shortlist":
            return (Verdict.ABSTAIN, _tray_msg(TrayMsgKey.ABSTAIN_SHORTLIST),
                    Action.SHORTLIST, Alert.WARNING)
        return Verdict.ABSTAIN, _tray_msg(TrayMsgKey.ABSTAIN), Action.RETRY, Alert.WARNING
    # An outcome the contract cannot express. Fail SAFE: never green.
    logger.warning("Tray well carried an unknown match outcome %r", outcome)
    return Verdict.ABSTAIN, _tray_msg(TrayMsgKey.ABSTAIN), Action.RETRY, Alert.WARNING


def slot_verdict(
    well: Dict[str, Any],
    *,
    profile_dins: List[str],
    allowlist,
    none_route: str = NoneRoute.DEFAULT,
    hedge: str = DEFAULT_HEDGE,
    canonicalise_din=lambda t: t,
) -> Dict[str, Any]:
    """One sidecar well -> one patient-facing slot.

    `well` is the contract's well object. `profile_dins` is the patient's FULL
    profile in SB2 token form (including the excluded members -- the scope note
    is computed from the full list, while only the supported subset was ever
    sent to the sidecar).
    """
    if none_route not in NoneRoute.ALL:
        raise ValueError(f"none_route must be one of {sorted(NoneRoute.ALL)}, got {none_route!r}")

    index = well.get("well")
    slot = int(index) + 1 if isinstance(index, int) else None
    occupied = bool(well.get("occupied"))
    error = well.get("error")
    match = well.get("match") or None

    out: Dict[str, Any] = {
        "slot": slot,
        "well": index,
        "occupied": occupied,
        "verdict": None,
        "action": Action.NONE,
        "alert": Alert.INFO,
        "terminal": False,
        "message": None,
        "notes": [],
        "decision": None,
        "abstain_action": None,
        "matched_din": None,
        "breakdown": None,
        "faces_seen": 0,
        "pharmacist_hedge": hedge,
        "error": error,
        "contract_error": None,
    }

    # 1. Nothing in the well. C.6 has nothing to say about an object that does
    #    not exist, so the message is a tray-layer one and the alert is INFO.
    if not occupied:
        out.update(verdict=Verdict.EMPTY, message=_tray_msg(TrayMsgKey.EMPTY, slot=slot),
                   action=Action.NONE, alert=Alert.INFO)
        return out

    # 2. Per-well failure isolation. The sidecar already caught it; we surface
    #    it as its own verdict rather than letting it masquerade as a decision.
    if error:
        out.update(verdict=Verdict.ERROR, message=_tray_msg(TrayMsgKey.ERROR, slot=slot),
                   action=Action.RETRY, alert=Alert.WARNING)
        out["notes"] = _scope_notes(profile_dins, allowlist)
        return out

    parsed, contract_error = record_view(well.get("record"))
    out["contract_error"] = contract_error
    out["faces_seen"] = len(parsed.faces)

    resolved = nb08_messages.resolve(parsed, profile_dins=profile_dins, allowlist=allowlist)
    notes = [msg_to_dict(n) for n in resolved.notes]

    # SB2's decision is recorded VERBATIM on every occupied slot, even when the
    # C.6 presence layer owns the user-facing message -- the same rule
    # routes/scans.py already holds, and dropping it would leave the audit
    # trail claiming SB2 never ran.
    #
    # `matched_din` and `breakdown` are the IDENTIFICATION, and they are held
    # back unless the identification is what the user is actually being shown.
    # Printing a DIN beside "turn the pill over" is a wrong-drug suggestion by
    # implication -- the same reasoning that keeps C.6's scope note anonymous.
    if match is not None:
        out["decision"] = match.get("outcome") or match.get("decision")
        out["abstain_action"] = match.get("abstain_action")

    # --- D-7 FAIL-SAFE DOWNGRADE (Muthu, 2026-08-14, binding) ---------------
    # A record that fails C6 validation is a record we do not understand, and
    # the contract's own rule is to refuse it rather than mis-read it. SB2
    # scored SOMETHING, but we cannot vouch for the object it scored, so its
    # decision must never reach the patient as a green verify.
    #
    # The downgrade is UNIFORM across decisions on purpose: branching on the
    # decision would make the verdict itself leak what the invalid record
    # said, which is the leak this rule exists to close. `decision` and
    # `abstain_action` are already recorded above and stay recorded -- the
    # audit trail must show that SB2 ran and what it concluded -- while
    # `matched_din` / `breakdown` are never populated on this path, the same
    # withholding rule the presence-owned branch applies.
    if contract_error:
        out.update(verdict=Verdict.ERROR,
                   message=_tray_msg(TrayMsgKey.ERROR_CONTRACT, slot=slot),
                   action=Action.ASK_PHARMACIST, alert=Alert.WARNING, terminal=False)
        out["notes"] = notes
        return out

    # 3. C.6 stayed quiet -> an imprint was read and cleared the margin gate,
    #    so the pill is identifiable and SB2's decision owns the result.
    if resolved.primary is None:
        if match is None:
            # A badge with no copy beside it is a cell the patient has to guess
            # at, so this state gets its own sentence like every other one.
            out.update(verdict=Verdict.READ_ONLY,
                       message=_tray_msg(TrayMsgKey.READ_ONLY, slot=slot),
                       action=Action.NONE, alert=Alert.INFO)
            return out
        verdict, message, action, alert = _decision_slot(match)
        out.update(verdict=verdict, message=message, action=action, alert=alert,
                   matched_din=canonicalise_din(match.get("matched_din")),
                   breakdown=match.get("breakdown"))
        # Never let "some of your list is not covered yet" ride alongside a
        # successful verification -- it reads as doubt about the one answer
        # the system is actually confident in.
        out["notes"] = [] if verdict == Verdict.VERIFY else notes
        return out

    # 4. A presence verdict owns the slot. Scope notes ride along (C.6
    #    precedence, Muthu 2026-08-11).
    key = resolved.primary.key
    out["notes"] = notes

    if key == nb08_messages.MsgKey.NO_IMPRINT:
        faces_seen = resolved.primary.params.get("faces_seen", out["faces_seen"])
        if none_route == NoneRoute.RETRY:
            # Muthu's call (3). PENDING: when this loop becomes terminal.
            out.update(verdict=Verdict.NO_IMPRINT,
                       message=_tray_msg(TrayMsgKey.NONE_RETRY, faces_seen=faces_seen, slot=slot),
                       action=Action.FLIP_RESHOOT, alert=Alert.WARNING, terminal=False)
        else:
            out.update(verdict=Verdict.NO_IMPRINT, message=msg_to_dict(resolved.primary),
                       action=Action.ASK_PHARMACIST, alert=Alert.WARNING, terminal=True)
        return out

    if key == nb08_messages.MsgKey.UNREADABLE:
        out.update(verdict=Verdict.UNREADABLE, message=msg_to_dict(resolved.primary),
                   action=Action.FLIP_RESHOOT, alert=Alert.WARNING, terminal=False)
        return out

    # Scope primaries (no_profile / unsupported) are frame-level and are
    # short-circuited before the sidecar is ever called. Reaching here means
    # the profile changed underneath us; surface it rather than hide it.
    out.update(verdict=Verdict.ABSTAIN, message=msg_to_dict(resolved.primary),
               action=Action.ASK_PHARMACIST, alert=Alert.WARNING,
               terminal=bool(resolved.terminal))
    return out


#: The only two verdicts allowed to drive a COLOURED (green/red) row on a
#: user-facing surface. Everything else -- including every D-7 downgrade --
#: collapses to the amber `abstain`, by DEFAULT rather than by enumeration, so
#: a verdict added later can never arrive green by omission.
_VERDICT_TO_DECISION = {Verdict.VERIFY: "verify", Verdict.REJECT: "reject"}


def decision_of_record(slot: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """The `(decision, abstain_action)` pair to PERSIST for one slot.

    THE DECISION OF RECORD IS THE SLOT VERDICT, NEVER SB2'S RAW DECISION
    ---------------------------------------------------------------------
    `slot["decision"]` is SB2's verbatim output, kept for the audit trail. It
    is NOT the decision of record. Persisting it into `analyses.decision` put
    it straight under `routes/scans.py`'s `_DECISION_TO_MATCH_STATUS`, so a
    slot D-7 had downgraded to `error` -- and a `no_imprint` slot whose
    identification was deliberately withheld -- listed in Safety Records as a
    GREEN "matched" row for the same pill the tray page said not to rely on.
    D-7 says a record we cannot validate NEVER shows as verified; that has to
    hold on every surface, not just the one the fix was written on.

    The collapse to `abstain` is UNIFORM for the same reason D-7's own
    downgrade is: branching on the raw decision would let the row's colour leak
    what the untrusted record said. `reject` is not reused for it either --
    refusing a record is not evidence the pill is wrong.

    `abstain_action` rides along only where the slot's OWN copy came from it
    (verdict `abstain`); elsewhere it is raw SB2 internals that Safety Records
    would print into `action_taken`. The raw pair belongs in `label_info`,
    audit detail no list/status mapping reads.
    """
    verdict = slot.get("verdict")
    if verdict == Verdict.EMPTY:
        return None, None
    decision = _VERDICT_TO_DECISION.get(verdict, "abstain")
    action = slot.get("abstain_action") if verdict == Verdict.ABSTAIN else None
    return decision, action


def _scope_notes(profile_dins: List[str], allowlist) -> List[Dict[str, Any]]:
    """The C.6 scope note on its own, for slots that never reach `resolve`
    (an errored well has no record to resolve against)."""
    unsupported = allowlist.unsupported(profile_dins)
    if not unsupported or len(unsupported) == len(profile_dins):
        return []
    return [{
        "key": nb08_messages.MsgKey.UNSUPPORTED_NOTE,
        "params": {"unsupported_n": len(unsupported), "profile_n": len(profile_dins)},
        "default_en": nb08_messages._EN[nb08_messages.MsgKey.UNSUPPORTED_NOTE],
        "provisional": False,
    }]


def empty_slots(count: int = SLOT_COUNT) -> List[Dict[str, Any]]:
    """A full grid of empty slots -- used to pad a short reply so the frontend
    always renders the same number of cells."""
    return [
        {
            "slot": i + 1, "well": i, "occupied": False, "verdict": Verdict.EMPTY,
            "action": Action.NONE, "alert": Alert.INFO, "terminal": False,
            "message": _tray_msg(TrayMsgKey.EMPTY, slot=i + 1), "notes": [],
            "decision": None, "abstain_action": None, "matched_din": None,
            "breakdown": None, "faces_seen": 0, "pharmacist_hedge": DEFAULT_HEDGE,
            "error": None, "contract_error": None,
        }
        for i in range(count)
    ]
