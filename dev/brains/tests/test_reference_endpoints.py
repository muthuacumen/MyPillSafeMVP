"""Offline tests for the sidecar's own reference endpoints.

Until now `dev/brains/` had no pytest module at all -- only the three
standalone smoke scripts (`smoke_test.py`, `qa_smoke_test.py`,
`parity_check.py`), every one of which needs the service already running.
That left the sidecar's own HTTP contract, and in particular the 2026-07-29
search score cutoff, guarded only by app-side tests one process away.

These run in-process through FastAPI's TestClient: no live service, no
Ollama, no GPU. They are deliberately about the SEARCH/REFERENCE contract
only -- pill analysis stays in `smoke_test.py`, because it needs real
images and a Paddle subprocess.

Run with the sidecar venv, from `dev/brains`:

    .\\.venv\\Scripts\\python.exe -m pytest tests -v

Importing `app` loads IMB1/SB2/BB3 and the 11,609-row profile CSV, so the
first test costs a few seconds. Anything genuinely unavailable in the
environment is SKIPPED with a reason rather than failed -- a deployment
without the profile CSV is a supported degraded mode, not a broken build.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as sidecar  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(sidecar.app)


requires_profile = pytest.mark.skipif(
    sidecar._PROFILE_DF is None,
    reason=f"profile reference not loaded: {sidecar._PROFILE_LOAD_ERROR}",
)
requires_sb2 = pytest.mark.skipif(
    sidecar.sb2_reference is None, reason="sb2 package not importable"
)

#: A real marketed Canadian DIN present in BOTH tiers, in the sidecar's own
#: token form (`"DIN"` + the UNPADDED integer -- the app's canonical
#: `"00013803"` becomes `"DIN13803"`).
GRAVOL = "DIN13803"


# --- /health ---------------------------------------------------------------

def test_health_reports_the_keys_callers_depend_on(client: TestClient):
    body = client.get("/health").json()
    for key in ("status", "imb1_ok", "sb2_ok", "bb3_ok", "ollama_up",
                "reference_rows", "profile_reference_rows", "rx_extract"):
        assert key in body, f"/health lost the {key!r} field callers rely on"
    # `ollama_up` is deliberately NOT asserted True: the sidecar must report
    # its degradation honestly, and these tests must pass with Ollama stopped.
    assert isinstance(body["ollama_up"], bool)


# --- /reference/search: the 2026-07-29 score cutoff ------------------------

def test_cutoff_constant_is_the_documented_value():
    """Guards the number itself. It was chosen by a pre-registered sweep
    (4 scorers x 9 cutoffs, 62 positives / 21 negatives); moving it silently
    would change how often `not_in_reference` warns the user."""
    assert sidecar.SEARCH_SCORE_CUTOFF == 75.0


@requires_profile
@pytest.mark.parametrize("q", ["GRAVOL", "LANTUS", "ATORVASTATIN", "AMOXICILLIN"])
def test_real_medications_still_return_suggestions(client: TestClient, q: str):
    """The cutoff must not cost recall on real drugs -- losing a suggestion
    breaks DIN linking, and without a linked DIN a pill cannot be verified
    at all."""
    rows = client.get("/reference/search", params={"q": q, "limit": 5}).json()
    assert rows, f"{q!r} returned nothing; the cutoff is too aggressive"
    assert any(q.split()[0] in str(r["product"]).upper() for r in rows)


@requires_profile
@pytest.mark.parametrize("q", [
    "ZZZQQQ", "XYZZY", "FLIMZAROL", "VERAXOLIN",     # nonsense / invented
    "COUMADIN",                                       # real brand, NOT Canadian
    "PHARMACY", "REFILLS", "QTY 30",                  # non-drug label text
])
def test_absent_medications_return_empty_so_the_flag_can_fire(client: TestClient, q: str):
    """THE regression guard for the cutoff.

    Before it existed, `process.extract` returned its top-N however bad they
    were: the nonsense query "ZZZQQQ 25 MG TAB" came back with the same
    confident 85.5-scoring candidates as a real digoxin query. The app's
    `flag_not_in_reference` guardrail fires ONLY on an empty list, so that
    junk reached the user with no warning -- and a wrongly linked DIN feeds
    SB2 a wrong appearance row and BB3 a wrong monograph.
    """
    rows = client.get("/reference/search", params={"q": q, "limit": 5}).json()
    assert rows == [], f"{q!r} should be unfindable, got {[r['product'] for r in rows]}"


@requires_profile
def test_every_returned_score_clears_the_cutoff(client: TestClient):
    rows = client.get("/reference/search", params={"q": "METFORMIN", "limit": 10}).json()
    assert rows
    assert all(r["score"] >= sidecar.SEARCH_SCORE_CUTOFF for r in rows)


@requires_profile
def test_search_result_shape_and_din_token_form(client: TestClient):
    rows = client.get("/reference/search", params={"q": "GRAVOL", "limit": 3}).json()
    assert rows
    row = rows[0]
    for key in ("din", "product", "strength", "score", "pill_verifiable"):
        assert key in row
    # SB2 token form: "DIN" + UNPADDED integer. The app converts at its own
    # boundary (`din_utils`), so drifting here breaks DIN linking silently.
    assert row["din"].startswith("DIN")
    assert row["din"][3:].isdigit()
    assert not row["din"][3:].startswith("0"), "token must be unpadded"
    assert isinstance(row["pill_verifiable"], bool)


@requires_profile
def test_blank_query_returns_empty_not_everything(client: TestClient):
    assert client.get("/reference/search", params={"q": "   "}).json() == []


@requires_profile
def test_limit_is_respected(client: TestClient):
    rows = client.get("/reference/search", params={"q": "METFORMIN", "limit": 2}).json()
    assert len(rows) <= 2


# --- /reference/profile (Task B2/B3 tier) ----------------------------------

@requires_profile
def test_profile_lookup_returns_pill_verifiable_for_a_known_din(client: TestClient):
    rows = client.get("/reference/profile", params={"dins": GRAVOL}).json()
    assert len(rows) == 1
    row = rows[0]
    assert row["din"] == GRAVOL
    for key in ("brand", "company", "ingredients", "forms", "routes",
                "schedules", "pill_verifiable"):
        assert key in row
    assert isinstance(row["pill_verifiable"], bool)


@requires_profile
def test_profile_lookup_omits_unknown_dins_rather_than_inventing_them(client: TestClient):
    """An absent DIN must be ABSENT from the answer, so the caller can tell
    "not in the tier" (empty list) from "the service is down" (no response).
    The app relies on this to keep `pill_verifiable` NULL rather than False --
    a wrong "can't be checked by photo" badge would teach a user not to
    verify a pill they actually could have verified."""
    rows = client.get("/reference/profile", params={"dins": "DIN99999999"}).json()
    assert rows == []


@requires_profile
def test_profile_lookup_handles_a_mixed_batch(client: TestClient):
    rows = client.get(
        "/reference/profile", params={"dins": f"{GRAVOL},DIN99999999"}
    ).json()
    assert [r["din"] for r in rows] == [GRAVOL]


# --- /reference/candidates (appearance tier SB2 matches against) -----------

@requires_sb2
def test_candidates_returns_the_appearance_contract_columns(client: TestClient):
    rows = client.get("/reference/candidates", params={"dins": GRAVOL}).json()
    assert len(rows) == 1
    row = rows[0]
    # The IMB1->SB2 contract columns. SB2's matcher reads these by name.
    for key in ("din", "product", "type_norm", "colour_norm_1", "colour_norm_2",
                "shape_norm", "imprint_side1", "imprint_side2", "imprint_status"):
        assert key in row, f"appearance row lost the {key!r} column SB2 matches on"


@requires_sb2
def test_candidates_unknown_din_returns_empty(client: TestClient):
    assert client.get("/reference/candidates", params={"dins": "DIN99999999"}).json() == []


@requires_sb2
def test_candidates_blank_input_returns_empty(client: TestClient):
    assert client.get("/reference/candidates", params={"dins": ""}).json() == []
