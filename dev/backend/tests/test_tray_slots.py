"""MPR1-T04 bars -- `/api/v1/tray/analyze`, N per-slot verdicts, C.6 messages.

The bars were FILED BEFORE THE CODE; the table lives in
`tests/artifacts/MPR1-T04/bars_filed.md` and each test below carries its bar id.

EVERY test runs against a MOCKED sidecar built from the FROZEN tray contract
(orchestrator, 2026-08-14). No service is started and neither :8100 nor :8101
is ever contacted -- the mock replaces `httpx.AsyncClient` wholesale, mirroring
`tests/test_pill_v2.py`'s idiom, and one bar (B14/B15) asserts the client is
never even CONSTRUCTED on the short-circuit paths.
"""
import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import Analysis
from app.services import nb08_messages, tray_messages
from app.services.allowlist import Allowlist, get_allowlist
from app.services.tray_messages import Action, Alert, TrayMsgKey, Verdict

# --- allowlist fixtures (Muthu's D-2: 11 supported / 4 excluded) --------------
SUPPORTED_GRAVOL = "13803"          # DIN13803  gravol      supported
SUPPORTED_MOTRIN = "2242658"        # DIN2242658 motrin     supported
EXCLUDED_BENYLIN = "2306409"        # DIN2306409 benylin    EXCLUDED
EXCLUDED_DINS = {"DIN2375990", "DIN2306409", "DIN2273462", "DIN2256452"}

THRESHOLD = 8.59  # the frozen D17-4 gate; `gated` must equal not(margin > threshold)

#: The frozen `match` block: exactly these four keys, nothing else. A mock that
#: invents a key manufactures a production path that cannot be reached, which
#: is how a dead branch shipped with a green bar over it (T09a, finding 3).
FROZEN_MATCH_KEYS = {"outcome", "abstain_action", "matched_din", "breakdown"}


# --- C6 record / contract builders -------------------------------------------


def _face(face_id: str, presence: str, *, top1=None, margin=None):
    """A C6 FaceRecord dict. `read` is ABSENT (not null-filled) unless presence
    is TEXT -- the contract rejects the null-filled form on purpose."""
    face = {"face_id": face_id, "rendering": "M0", "presence": presence,
            "presence_source": "stage1.A3"}
    if presence == "TEXT":
        face["read"] = {"top1": top1, "margin": margin, "gated": not (margin > THRESHOLD),
                        "threshold": THRESHOLD, "lexicon_id": "lex-t04", "arm": "A4c"}
    return face


def _record(faces, *, detected=True, shadow=False):
    return {
        "detected": detected, "photo": "tray.jpg", "contract_version": "C6",
        "colour_modes": [{"top2": [["orange", 0.72], ["peach", 0.21]]}],
        "shape_out": "round", "shape_conf": 0.91, "type_out": "tablet", "type_conf": 0.5,
        "faces": faces, "lexicon_profile_dins": ["DIN13803"],
        "diagnostics": {"shadow_fusion_suspected": shadow},
    }


RECORD_READ = _record([_face("f0", "TEXT", top1="GRAVOL", margin=12.0)])
RECORD_GATED = _record([_face("f0", "TEXT", top1="GRAVOL", margin=1.0)])
RECORD_UNREADABLE = _record([_face("f0", "UNREADABLE")])
RECORD_NONE = _record([_face("f0", "NONE"), _face("f1", "NONE")])

BREAKDOWN = {"S": 0.91, "colour_score": 1.0, "shape_score": 1.0, "type_score": 1.0,
             "imprint_exact": True, "imprint_fuzzy": 1.0}


def _match(outcome, *, abstain_action=None, matched_din=None):
    return {"outcome": outcome, "abstain_action": abstain_action,
            "matched_din": matched_din, "breakdown": BREAKDOWN}


def _well(i, *, occupied=True, record=None, match=None, error=None):
    return {"well": i, "occupied": occupied, "record": record, "match": match, "error": error}


def _tray(wells):
    return {"tray": True, "pipeline": "pipe11-v1", "wells": wells,
            "timing_ms": {"total": 4210, "localise": 120, "read": 3600, "match": 490}}


def _full_tray(match_outcome="verify", *, record=RECORD_READ, abstain_action=None):
    """Well 0 carries the interesting case; wells 1..5 are empty."""
    return _tray(
        [_well(0, record=record,
               match=_match(match_outcome, abstain_action=abstain_action,
                            matched_din="DIN13803" if match_outcome == "verify" else None))]
        + [_well(i, occupied=False) for i in range(1, 6)]
    )


# --- the mocked sidecar -------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakeSidecar:
    """Stands in for httpx.AsyncClient. Class-level knobs let each bar pick the
    canned reply and the status code."""

    response_body: dict = {}
    status_code: int = 200
    last_kwargs: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        _FakeSidecar.last_kwargs = {"url": url, **kwargs}
        return _FakeResponse(_FakeSidecar.status_code, _FakeSidecar.response_body)


class _Unreachable:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    async def get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))


class _NeverCalled:
    def __init__(self, *args, **kwargs):
        raise AssertionError(
            "httpx.AsyncClient must not be constructed -- this path short-circuits "
            "before the sidecar"
        )


# --- helpers ------------------------------------------------------------------


async def _confirm(client: AsyncClient, headers: dict, din: str) -> str:
    resp = await client.post("/api/v1/prescriptions", headers=headers,
                             files={"image": ("rx.jpg", b"fake-bytes", "image/jpeg")})
    pid = resp.json()[0]["id"]
    patch = await client.patch(f"/api/v1/prescriptions/{pid}", headers=headers, json={"din": din})
    assert patch.json()["din_confirmed"] is True
    return pid


async def _arm(monkeypatch, client, headers, body, *, dins=(SUPPORTED_GRAVOL,), status_code=200):
    """Create the profile against an unreachable sidecar (create-time DIN
    suggestion attach is allowed to fail), then swap in the tray mock."""
    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _Unreachable)
    for din in dins:
        await _confirm(client, headers, din)
    _FakeSidecar.response_body = body
    _FakeSidecar.status_code = status_code
    _FakeSidecar.last_kwargs = None
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecar)


async def _post(client: AsyncClient, headers: dict, **data):
    return await client.post("/api/v1/tray/analyze", headers=headers,
                             files={"photo": ("tray.jpg", b"fake-bytes", "image/jpeg")},
                             data=data or None)


def _sent_dins() -> list[str]:
    return json.loads(_FakeSidecar.last_kwargs["data"]["profile_dins"])


# =============================================================================
# B01 -- slot mapping
# =============================================================================


@pytest.mark.asyncio
async def test_B01_slot_mapping_well_k_to_slot_k_plus_1(client, auth_headers, monkeypatch):
    wells = [_well(i, record=RECORD_READ, match=_match("verify", matched_din="DIN13803"))
             for i in range(6)]
    await _arm(monkeypatch, client, auth_headers, _tray(wells))

    body = (await _post(client, auth_headers)).json()
    assert [s["well"] for s in body["slots"]] == [0, 1, 2, 3, 4, 5]
    assert [s["slot"] for s in body["slots"]] == [1, 2, 3, 4, 5, 6]
    assert body["slot_count"] == 6


# =============================================================================
# B02-B06 -- verdict -> message matrix (SB2 decision path)
# =============================================================================


@pytest.mark.asyncio
async def test_B02_verdict_verify_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.VERIFY
    assert slot["message"]["key"] == TrayMsgKey.VERIFY
    assert slot["alert"] == Alert.OK
    assert slot["action"] == Action.NONE
    assert slot["terminal"] is False
    assert slot["decision"] == "verify"
    assert slot["matched_din"] == "00013803"  # canonical, never the token form


@pytest.mark.asyncio
async def test_B03_verdict_reject_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("reject"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.REJECT
    assert slot["message"]["key"] == TrayMsgKey.REJECT
    assert slot["alert"] == Alert.DANGER
    assert slot["matched_din"] is None


@pytest.mark.asyncio
async def test_B04_verdict_abstain_ask_to_flip_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers,
               _full_tray("abstain", abstain_action="ask_to_flip"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.ABSTAIN
    assert slot["verdict"] != Verdict.REJECT  # abstain must never collapse into reject
    assert slot["message"]["key"] == TrayMsgKey.ABSTAIN_ASK_TO_FLIP
    assert slot["action"] == Action.FLIP_RESHOOT
    assert slot["abstain_action"] == "ask_to_flip"
    assert slot["alert"] == Alert.WARNING


@pytest.mark.asyncio
async def test_B05_verdict_abstain_shortlist_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers,
               _full_tray("abstain", abstain_action="shortlist"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["message"]["key"] == TrayMsgKey.ABSTAIN_SHORTLIST
    assert slot["action"] == Action.SHORTLIST


@pytest.mark.asyncio
async def test_B06_verdict_abstain_bare_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("abstain"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["message"]["key"] == TrayMsgKey.ABSTAIN
    assert slot["action"] == Action.RETRY


# =============================================================================
# B07/B08 -- error isolation and empty wells
# =============================================================================


@pytest.mark.asyncio
async def test_B07_occupied_with_error_isolated(client, auth_headers, monkeypatch):
    wells = [
        _well(0, error="read: CUDA OOM in stage 2"),
        _well(1, record=RECORD_READ, match=_match("verify", matched_din="DIN13803")),
    ] + [_well(i, occupied=False) for i in range(2, 6)]
    await _arm(monkeypatch, client, auth_headers, _tray(wells))

    resp = await _post(client, auth_headers)
    assert resp.status_code == 200  # one bad well never fails the frame
    slots = resp.json()["slots"]
    assert slots[0]["verdict"] == Verdict.ERROR
    assert slots[0]["message"]["key"] == TrayMsgKey.ERROR
    assert slots[0]["error"] == "read: CUDA OOM in stage 2"
    assert slots[0]["decision"] is None
    assert slots[1]["verdict"] == Verdict.VERIFY  # sibling unaffected
    assert slots[1]["error"] is None


@pytest.mark.asyncio
async def test_B08_unoccupied_slot_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"))
    body = (await _post(client, auth_headers)).json()
    empty = body["slots"][3]
    assert empty["occupied"] is False
    assert empty["verdict"] == Verdict.EMPTY
    assert empty["message"]["key"] == TrayMsgKey.EMPTY
    assert empty["alert"] == Alert.INFO
    assert empty["decision"] is None
    assert len(body["analysis_ids"]) == 1  # only the one occupied well persisted


# =============================================================================
# B09/B10 -- NONE faces: retry (default) vs terminal (the parameter)
# =============================================================================


@pytest.mark.asyncio
async def test_B09_none_faces_retry_route_default(client, auth_headers, monkeypatch):
    """Muthu's filed tray call (3): in the TRAY flow NONE routes to
    Flip/Reshoot alongside UNREADABLE, deviating from single-pill terminal
    semantics. Default, no parameter supplied."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("abstain", record=RECORD_NONE))
    body = (await _post(client, auth_headers)).json()
    assert body["none_route"] == "retry"
    slot = body["slots"][0]
    assert slot["verdict"] == Verdict.NO_IMPRINT
    assert slot["message"]["key"] == TrayMsgKey.NONE_RETRY
    assert slot["message"]["provisional"] is True
    assert slot["action"] == Action.FLIP_RESHOOT
    assert slot["terminal"] is False
    assert slot["faces_seen"] == 2


@pytest.mark.asyncio
async def test_B10_none_faces_terminal_route_param(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("abstain", record=RECORD_NONE))
    body = (await _post(client, auth_headers, none_route="terminal")).json()
    assert body["none_route"] == "terminal"
    slot = body["slots"][0]
    assert slot["verdict"] == Verdict.NO_IMPRINT
    assert slot["message"]["key"] == nb08_messages.MsgKey.NO_IMPRINT  # pill.presence.none
    assert slot["message"]["provisional"] is False
    assert slot["action"] == Action.ASK_PHARMACIST
    assert slot["terminal"] is True


@pytest.mark.asyncio
async def test_B10b_bad_none_route_rejected(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"))
    resp = await _post(client, auth_headers, none_route="sometimes")
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"]["code"] == "TRAY_BAD_NONE_ROUTE"


# =============================================================================
# B11 -- UNREADABLE faces
# =============================================================================


@pytest.mark.asyncio
async def test_B11_unreadable_faces_message(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("abstain", record=RECORD_UNREADABLE))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.UNREADABLE
    assert slot["message"]["key"] == nb08_messages.MsgKey.UNREADABLE
    assert slot["message"]["params"] == {"faces_seen": 1, "unseen_face_possible": True}
    assert slot["action"] == Action.FLIP_RESHOOT
    assert slot["terminal"] is False


@pytest.mark.asyncio
async def test_B23_presence_owned_slot_records_decision_but_withholds_identification(
    client, auth_headers, monkeypatch
):
    """When C.6's presence verdict owns the slot, SB2's decision is still
    recorded verbatim (audit), but `matched_din` is withheld -- a DIN printed
    beside "turn the pill over" is a wrong-drug suggestion by implication."""
    tray = _full_tray("abstain", record=RECORD_NONE, abstain_action="ask_to_flip")
    tray["wells"][0]["match"]["matched_din"] = "DIN13803"
    await _arm(monkeypatch, client, auth_headers, tray)
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.NO_IMPRINT
    assert slot["decision"] == "abstain"
    assert slot["abstain_action"] == "ask_to_flip"
    assert slot["matched_din"] is None
    assert slot["breakdown"] is None


# =============================================================================
# D7a-D7c -- Muthu's decision D-7: FAIL-SAFE DOWNGRADE on an invalid record
# =============================================================================

#: Parses fine, fails C6 validation: the contract refuses a record whose
#: version it does not understand rather than mis-reading it.
RECORD_BAD_CONTRACT = {**RECORD_READ, "contract_version": "C5"}


@pytest.mark.asyncio
async def test_D7a_contract_error_downgrades_sb2_verify(client, auth_headers, monkeypatch):
    """D-7 (binding): a slot whose record fails C6 validation must NEVER carry
    verdict `verify`. SB2's raw decision is kept for the audit trail; the
    identification is withheld and the user is sent to a pharmacist."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify", record=RECORD_BAD_CONTRACT))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.ERROR
    assert slot["verdict"] != Verdict.VERIFY
    assert slot["contract_error"] is not None and "C6" in slot["contract_error"]
    assert slot["decision"] == "verify"      # verbatim, for audit
    assert slot["matched_din"] is None       # identification withheld
    assert slot["breakdown"] is None
    assert slot["action"] == Action.ASK_PHARMACIST
    assert slot["alert"] == Alert.WARNING
    assert slot["message"]["key"] == TrayMsgKey.ERROR_CONTRACT


@pytest.mark.asyncio
async def test_D7b_contract_error_downgrades_sb2_reject(client, auth_headers, monkeypatch):
    """UNIFORM by design: if the downgrade varied with the decision, the
    verdict itself would leak what the invalid record said."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("reject", record=RECORD_BAD_CONTRACT))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.ERROR
    assert slot["decision"] == "reject"
    assert slot["matched_din"] is None
    assert slot["message"]["key"] == TrayMsgKey.ERROR_CONTRACT


@pytest.mark.asyncio
async def test_D7c_valid_record_still_verifies(client, auth_headers, monkeypatch):
    """The control. Without this, D-7 could be 'satisfied' by breaking verify
    everywhere."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["contract_error"] is None
    assert slot["verdict"] == Verdict.VERIFY
    assert slot["matched_din"] == "00013803"


@pytest.mark.asyncio
async def test_B11b_gated_read_is_unreadable_not_verified(client, auth_headers, monkeypatch):
    """The margin gate is the safety mechanism: a below-threshold read must
    never reach the matcher's copy path."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("abstain", record=RECORD_GATED))
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.UNREADABLE
    assert slot["message"]["key"] == nb08_messages.MsgKey.UNREADABLE


# =============================================================================
# B12 -- DIN token-form regression
# =============================================================================


@pytest.mark.asyncio
async def test_B12_token_form_regression_padded_and_bare(client, auth_headers, monkeypatch):
    """The documented trap: a zero-padded token yields an EMPTY ballot and SB2
    returns a `reject` indistinguishable from a genuine rejection. Both input
    forms must leave through `din_utils.to_sb2_token` as `DIN13803`."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"),
               dins=("00013803", "13803"))
    await _post(client, auth_headers)
    sent = _sent_dins()
    assert sent == ["DIN13803"]
    assert not any(d.startswith("DIN0") for d in sent)


# =============================================================================
# B13-B15 -- allowlist filtering and the two short-circuits
# =============================================================================


@pytest.mark.asyncio
async def test_B13_excluded_din_never_sent_and_notice_emitted(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers, _full_tray("reject"),
               dins=(SUPPORTED_GRAVOL, EXCLUDED_BENYLIN))
    body = (await _post(client, auth_headers)).json()

    sent = _sent_dins()
    assert "DIN2306409" not in sent  # the excluded med is never scored
    assert sent == ["DIN13803"]

    profile = body["profile"]
    assert profile == {"profile_n": 2, "supported_n": 1, "unsupported_n": 1,
                       "notice": profile["notice"]}
    assert profile["notice"]["key"] == nb08_messages.MsgKey.UNSUPPORTED_NOTE
    assert profile["notice"]["params"] == {"unsupported_n": 1, "profile_n": 2}
    # Verify-Don't-Identify: no slot may claim a pill is "the unsupported one".
    for slot in body["slots"]:
        assert slot["message"] is None or "unsupported" not in slot["message"]["key"]


@pytest.mark.asyncio
async def test_B14_all_unsupported_profile_short_circuits(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _Unreachable)
    await _confirm(client, auth_headers, EXCLUDED_BENYLIN)

    monkeypatch.setattr(httpx, "AsyncClient", _NeverCalled)
    resp = await _post(client, auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unsupported_profile"
    assert body["message"]["key"] == nb08_messages.MsgKey.UNSUPPORTED
    assert body["terminal"] is True
    assert body["profile"]["supported_n"] == 0
    assert body["profile"]["notice"] is None  # not said twice
    assert len(body["slots"]) == 6
    assert body["analysis_ids"] == []


@pytest.mark.asyncio
async def test_B15_empty_profile_short_circuits(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _NeverCalled)
    resp = await _post(client, auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_profile"
    assert body["message"]["key"] == nb08_messages.MsgKey.NO_PROFILE
    assert body["terminal"] is True
    assert len(body["slots"]) == 6


# =============================================================================
# B16/B19 -- frame-level failures
# =============================================================================


@pytest.mark.asyncio
async def test_B16_frame_level_4xx_passthrough(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers,
               {"error": "localise: no tray found in frame"}, status_code=422)
    resp = await _post(client, auth_headers)
    assert resp.status_code == 422
    assert resp.json() == {"error": "localise: no tray found in frame"}


@pytest.mark.asyncio
async def test_B19_sidecar_unreachable_503(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _Unreachable)
    await _confirm(client, auth_headers, SUPPORTED_GRAVOL)
    resp = await _post(client, auth_headers)
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"]["code"] == "BRAINS_UNAVAILABLE"


# =============================================================================
# B17 -- persistence
# =============================================================================


@pytest.mark.asyncio
async def test_B17_per_slot_persistence_n_rows(
    client, auth_headers, monkeypatch, db_session: AsyncSession
):
    wells = [
        _well(0, record=RECORD_READ, match=_match("verify", matched_din="DIN13803")),
        _well(1, record=RECORD_READ, match=_match("reject")),
        _well(2, record=RECORD_NONE, match=_match("abstain", abstain_action="ask_to_flip")),
    ] + [_well(i, occupied=False) for i in range(3, 6)]
    await _arm(monkeypatch, client, auth_headers, _tray(wells))

    body = (await _post(client, auth_headers)).json()
    assert len(body["analysis_ids"]) == 3  # three occupied wells, three rows

    rows = (await db_session.execute(
        select(Analysis).where(Analysis.id.in_(body["analysis_ids"]))
    )).scalars().all()
    assert len(rows) == 3
    by_slot = {r.label_info["slot"]: r for r in rows}
    assert sorted(by_slot) == [1, 2, 3]
    assert all(r.label_info["tray"] is True for r in rows)
    assert len({r.label_info["tray_scan_id"] for r in rows}) == 1  # one photo, one scan id
    assert by_slot[1].decision == "verify" and by_slot[1].matched_din == "00013803"
    assert by_slot[2].decision == "reject" and by_slot[2].matched_din is None
    # Slot 3's SLOT VERDICT is `no_imprint` (C.6 presence owns it), so the
    # DECISION OF RECORD is the amber `abstain` and NO raw abstain_action
    # reaches the record surface -- `action_taken` in Safety Records would
    # otherwise print SB2's "ask_to_flip" beside a slot whose own copy says
    # something else. The raw pair stays in `label_info`, audit detail that no
    # list/status mapping reads (T09a, finding 1).
    assert by_slot[3].decision == "abstain"
    assert by_slot[3].abstain_action is None
    assert by_slot[3].label_info["sb2_decision"] == "abstain"
    assert by_slot[3].label_info["sb2_abstain_action"] == "ask_to_flip"
    assert by_slot[1].top_candidate_score == 0.91

    # Safety Records renders tray rows with no changes to that surface.
    listed = (await client.get("/api/v1/scans/me", headers=auth_headers)).json()
    assert {r["match_status"] for r in listed} == {"matched", "unmatched", "warning"}


# =============================================================================
# B18/B21/B22 -- auth, hedge, grid shape
# =============================================================================


@pytest.mark.asyncio
async def test_B18_requires_auth(client):
    resp = await client.post("/api/v1/tray/analyze",
                             files={"photo": ("tray.jpg", b"x", "image/jpeg")})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_B21_pharmacist_hedge_present_on_every_slot_from_one_source(
    client, auth_headers, monkeypatch
):
    """Muthu's filed tray call (2): per-slot alert payloads AND the pharmacist
    hedge, empty slots included.

    DISCRIMINATING FORM (T09a, finding 3). The old bar compared the hedge to a
    literal that was byte-identical to `tray_messages.DEFAULT_HEDGE`, so it
    passed whichever source produced it. This one pins a SENTINEL onto the
    single declared source and feeds the route a well whose `match` carries an
    out-of-contract `disclaimer` -- the second source that used to exist. If
    any second source is ever re-introduced its string wins and this goes red.
    """
    sentinel = "SENTINEL HEDGE -- T09a single-source bar"
    intruder = "SIDECAR DISCLAIMER MUST NOT WIN"
    tray = _full_tray("verify")
    # DELIBERATELY off-contract: the frozen match shape is exactly
    # {outcome, abstain_action, matched_din, breakdown} and has no disclaimer.
    tray["wells"][0]["match"]["disclaimer"] = intruder
    await _arm(monkeypatch, client, auth_headers, tray)
    monkeypatch.setattr(tray_messages, "DEFAULT_HEDGE", sentinel)

    body = (await _post(client, auth_headers)).json()
    slots = body["slots"]
    assert len(slots) == 6
    for slot in slots:
        assert slot["pharmacist_hedge"] == sentinel
        assert slot["alert"] in {Alert.OK, Alert.WARNING, Alert.DANGER, Alert.INFO}
    assert intruder not in json.dumps(body)


@pytest.mark.asyncio
async def test_B22_slot_count_always_six(client, auth_headers, monkeypatch):
    await _arm(monkeypatch, client, auth_headers,
               _tray([_well(0, record=RECORD_READ, match=_match("verify", matched_din="DIN13803"))]))
    slots = (await _post(client, auth_headers)).json()["slots"]
    assert len(slots) == 6
    assert [s["slot"] for s in slots] == [1, 2, 3, 4, 5, 6]
    assert all(s["verdict"] == Verdict.EMPTY for s in slots[1:])


# =============================================================================
# B20 -- allowlist integrity (pure unit, no route)
# =============================================================================


def test_B20_allowlist_integrity_11_supported_4_excluded():
    allow = get_allowlist()
    assert len(allow.dins()) == 11
    excluded = set(allow.universe()) - set(allow.dins())
    assert excluded == EXCLUDED_DINS
    assert allow.is_supported("DIN13803") is True
    assert allow.is_supported("DIN2306409") is False
    assert allow.is_supported("DIN99999999") is False  # absent == unsupported (4.2)
    assert allow.unsupported(["DIN13803", "DIN2306409"]) == ["DIN2306409"]
    assert allow.supported_subset(["DIN2306409", "DIN13803"]) == ["DIN13803"]


def test_B20b_padded_din_is_a_hard_error_not_a_silent_repad():
    with pytest.raises(ValueError, match="zero-padded"):
        get_allowlist().is_supported("DIN00013803")


def test_B20c_empty_allowlist_supports_nothing():
    """An empty allowlist means 'nothing is supported yet', never 'fall back
    to a default'."""
    empty = Allowlist.from_records([])
    assert empty.dins() == []
    assert empty.supported_subset(["DIN13803"]) == []
    assert empty.unsupported(["DIN13803"]) == ["DIN13803"]


def test_F3a_mock_match_block_is_the_frozen_four_key_shape():
    """T09a, finding 3. The mock is the only description of the sidecar this
    suite ever sees, so a mock that emits a key the frozen contract does not
    have manufactures a production code path nobody can reach."""
    assert set(_match("verify", matched_din="DIN13803")) == FROZEN_MATCH_KEYS
    assert set(_match("abstain", abstain_action="shortlist")) == FROZEN_MATCH_KEYS
    for well in _full_tray("verify")["wells"]:
        if well["match"] is not None:
            assert set(well["match"]) == FROZEN_MATCH_KEYS


def test_B20d_provisional_keys_are_declared_outside_the_c6_closed_set():
    """Every tray key is PROVISIONAL and none of them silently shadows a C.6
    key -- the gap has to stay visible."""
    assert TrayMsgKey.ALL == TrayMsgKey.PROVISIONAL
    assert not (TrayMsgKey.ALL & nb08_messages.MsgKey.ALL)
    assert set(tray_messages._TRAY_EN) == TrayMsgKey.ALL
    for copy in tray_messages._TRAY_EN.values():
        assert copy.isascii(), copy


# =============================================================================
# MPR1-T09a -- repairs to the T08 refutation's backend findings.
# Bars filed and run RED before any of the fixes were written; the reds are in
# tests/artifacts/MPR1-T09a/.
# =============================================================================


@pytest.mark.asyncio
async def test_F1a_d7_downgraded_slot_is_never_matched_in_safety_records(
    client, auth_headers, monkeypatch, db_session: AsyncSession
):
    """[BLOCKER 1] The DECISION OF RECORD is the SLOT VERDICT, never SB2's raw
    decision. A D-7 downgraded slot used to persist `decision="verify"`, which
    `routes/scans.py` maps to a GREEN "matched" row -- Safety Records told the
    patient the same pill was verified that the tray page told them not to
    rely on. The raw decision survives ONLY in `label_info`, audit detail no
    list/status mapping reads.
    """
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify", record=RECORD_BAD_CONTRACT))
    body = (await _post(client, auth_headers)).json()
    assert body["slots"][0]["verdict"] == Verdict.ERROR  # D-7 held on the tray page

    listed = (await client.get("/api/v1/scans/me", headers=auth_headers)).json()
    assert len(listed) == 1
    row = listed[0]
    assert row["match_status"] != "matched"
    assert row["match_status"] == "warning"       # amber: we cannot vouch either way
    assert row["decision"] != "verify"
    assert "verify" not in row["action_taken"]
    assert row["matched_din"] is None
    assert row["drug_name"] is None

    stored = (await db_session.execute(
        select(Analysis).where(Analysis.id == body["analysis_ids"][0])
    )).scalars().one()
    assert stored.label_info["verdict"] == Verdict.ERROR
    assert stored.label_info["sb2_decision"] == "verify"  # audit trail intact


@pytest.mark.asyncio
async def test_F1b_no_imprint_slot_with_raw_verify_is_never_matched(
    client, auth_headers, monkeypatch
):
    """[BLOCKER 1, second surface] B23's own call: a presence-owned slot
    records SB2's decision for audit. That record must still not colour a
    Safety Records row green."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify", record=RECORD_NONE))
    body = (await _post(client, auth_headers)).json()
    assert body["slots"][0]["verdict"] == Verdict.NO_IMPRINT

    row = (await client.get("/api/v1/scans/me", headers=auth_headers)).json()[0]
    assert row["match_status"] != "matched"
    assert row["decision"] != "verify"


@pytest.mark.asyncio
async def test_F1c_clean_verify_slot_still_lists_as_matched(client, auth_headers, monkeypatch):
    """The control. Without it, F1a/F1b could be 'satisfied' by making every
    tray row amber."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"))
    body = (await _post(client, auth_headers)).json()
    assert body["slots"][0]["verdict"] == Verdict.VERIFY

    row = (await client.get("/api/v1/scans/me", headers=auth_headers)).json()[0]
    assert row["match_status"] == "matched"
    assert row["decision"] == "verify"
    assert row["matched_din"] == "00013803"


def test_F2a_tray_analyze_ships_disabled_by_default():
    """[SERIOUS 5, backend half] Default-on shipped the feature at the next
    routine deploy, against a production sidecar with no `/tray/analyze`.
    `_env_file=None` reads the SHIPPED default, not this machine's .env."""
    from app.core.config import Settings

    assert Settings(_env_file=None).TRAY_ANALYZE_ENABLED is False


@pytest.mark.asyncio
async def test_F2b_shipped_default_makes_the_route_501(client, auth_headers, monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED",
                        Settings(_env_file=None).TRAY_ANALYZE_ENABLED)
    resp = await _post(client, auth_headers)
    assert resp.status_code == 501
    assert resp.json()["detail"]["error"]["code"] == "TRAY_ANALYZE_DISABLED"


@pytest.mark.asyncio
async def test_F4a_duplicate_prescriptions_of_one_din_count_once(
    client, auth_headers, monkeypatch
):
    """[MINOR 9] Two prescriptions of one DIN are one medication as far as
    coverage goes. `unsupported` was already deduped, `profile_n` was not, so
    the notice read "1 of 3 not covered" for a two-medication profile."""
    await _arm(monkeypatch, client, auth_headers, _full_tray("verify"),
               dins=(SUPPORTED_GRAVOL, SUPPORTED_GRAVOL, EXCLUDED_BENYLIN))
    profile = (await _post(client, auth_headers)).json()["profile"]
    assert profile["profile_n"] == 2
    assert profile["supported_n"] == 1
    assert profile["unsupported_n"] == 1
    assert profile["notice"]["params"] == {"unsupported_n": 1, "profile_n": 2}
    assert _sent_dins() == ["DIN13803"]


@pytest.mark.asyncio
async def test_F4b_duplicate_excluded_din_is_wholly_uncovered_and_says_so_once(
    client, auth_headers, monkeypatch
):
    """[MINOR 9, the short-circuit half] On the same basis the profile is
    WHOLLY uncovered, so the note is promoted to the frame message and the
    count-only notice must not be emitted as well -- saying it twice is the
    exact thing `_profile_block` documents it will not do."""
    monkeypatch.setattr(settings, "TRAY_ANALYZE_ENABLED", True)
    monkeypatch.setattr(httpx, "AsyncClient", _Unreachable)
    await _confirm(client, auth_headers, EXCLUDED_BENYLIN)
    await _confirm(client, auth_headers, EXCLUDED_BENYLIN)

    monkeypatch.setattr(httpx, "AsyncClient", _NeverCalled)
    body = (await _post(client, auth_headers)).json()
    assert body["status"] == "unsupported_profile"
    assert body["profile"] == {"profile_n": 1, "supported_n": 0, "unsupported_n": 1,
                               "notice": None}


@pytest.mark.asyncio
async def test_F5_read_only_slot_always_carries_copy(client, auth_headers, monkeypatch):
    """[MINOR 11, backend half] `read_only` rendered a badge with no message,
    so the cell had a colour and nothing to read."""
    tray = _tray([_well(0, record=RECORD_READ, match=None)]
                 + [_well(i, occupied=False) for i in range(1, 6)])
    await _arm(monkeypatch, client, auth_headers, tray)
    slot = (await _post(client, auth_headers)).json()["slots"][0]
    assert slot["verdict"] == Verdict.READ_ONLY
    assert slot["message"] is not None
    assert slot["message"]["key"] == TrayMsgKey.READ_ONLY
    assert slot["message"]["provisional"] is True
    assert slot["message"]["default_en"].isascii()
