"""FixbyOPUS3 Task A1/A5 -- the sidecar's `POST /rx/extract`, with Ollama
mocked at the transport boundary (`rx_extract._post_chat`).

The module under test lives in `dev/brains/`, not in this package. It is
imported by path on purpose: `rx_extract.py` is deliberately free of
imb1/sb2/bb3 (and therefore of torch/paddle) so it can be exercised from the
backend's own venv, in this suite, on every run -- rather than only by hand
against a live sidecar. The sidecar mounts the very same `APIRouter` these
tests drive, so what is tested here is the shipped endpoint, not a copy.
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BRAINS_DIR = Path(__file__).resolve().parents[2] / "brains"
if str(_BRAINS_DIR) not in sys.path:
    sys.path.insert(0, str(_BRAINS_DIR))

import rx_extract  # noqa: E402


@pytest.fixture
def rx_client() -> TestClient:
    app = FastAPI()
    app.include_router(rx_extract.router)
    return TestClient(app)


_LABEL = (
    "Shoppers Drug Mart #1123\n"
    "APO-AMLODIPINE 5 MG TABLET\n"
    "TAKE 1 TABLET BY MOUTH ONCE DAILY\n"
)

_GOOD_JSON = (
    '{"medications": [{"drug_name": "APO-AMLODIPINE 5 MG TABLET", '
    '"dosage": "5 mg", "frequency_type": "ONCE_DAILY", '
    '"explicit_times": [], "with_food": false}]}'
)


def test_good_json_returns_medications(rx_client, monkeypatch):
    monkeypatch.setattr(rx_extract, "_post_chat", lambda messages, timeout: _GOOD_JSON)
    response = rx_client.post("/rx/extract", json={"raw_text": _LABEL})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == rx_extract.RX_MODEL
    assert body["retried"] is False
    assert "elapsed_seconds" in body
    assert body["medications"] == [{
        "drug_name": "APO-AMLODIPINE 5 MG TABLET",
        "dosage": "5 mg",
        "frequency_type": "ONCE_DAILY",
        "explicit_times": [],
        "with_food": False,
    }]


def test_malformed_then_good_json_succeeds_via_corrective_retry(rx_client, monkeypatch):
    calls = {"n": 0}

    def _fake_post(messages, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return "Sure! Here are the medications I found: (no JSON here)"
        # The retry must carry the failed reply plus the corrective
        # instruction, not just re-ask the original question.
        assert any(rx_extract._RETRY_INSTRUCTION in m["content"] for m in messages)
        return _GOOD_JSON

    monkeypatch.setattr(rx_extract, "_post_chat", _fake_post)
    response = rx_client.post("/rx/extract", json={"raw_text": _LABEL})
    assert response.status_code == 200
    assert response.json()["retried"] is True
    assert calls["n"] == 2


def test_unparseable_twice_returns_typed_error(rx_client, monkeypatch):
    monkeypatch.setattr(rx_extract, "_post_chat", lambda messages, timeout: "still not json")
    response = rx_client.post("/rx/extract", json={"raw_text": _LABEL})
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "MODEL_OUTPUT_UNPARSEABLE"


def test_ollama_down_returns_typed_error(rx_client, monkeypatch):
    def _down(messages, timeout):
        raise rx_extract.RxExtractError("OLLAMA_UNREACHABLE", "connection refused")

    monkeypatch.setattr(rx_extract, "_post_chat", _down)
    response = rx_client.post("/rx/extract", json={"raw_text": _LABEL})
    assert response.status_code == 503
    error = response.json()["detail"]["error"]
    assert error["code"] == "OLLAMA_UNREACHABLE"


def test_empty_raw_text_is_a_typed_error_not_an_empty_success(rx_client):
    """"The model found nothing" and "the model never ran" must never look
    the same to the backend -- that distinction is what keeps a failed scan
    from being saved as a prescription with no medications."""
    response = rx_client.post("/rx/extract", json={"raw_text": "   "})
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "EMPTY_RAW_TEXT"


def test_medication_list_is_capped_and_schema_coerced(rx_client, monkeypatch):
    payload = {"medications": [
        {"drug_name": f"DRUG {i}", "dosage": None, "frequency_type": "SOMETIMES",
         "explicit_times": "not a list", "with_food": "yes"}
        for i in range(40)
    ]}
    import json as json_mod
    monkeypatch.setattr(rx_extract, "_post_chat", lambda messages, timeout: json_mod.dumps(payload))
    response = rx_client.post("/rx/extract", json={"raw_text": _LABEL})
    assert response.status_code == 200
    meds = response.json()["medications"]
    assert len(meds) == rx_extract.MAX_MEDICATIONS == 20
    assert meds[0]["frequency_type"] == "UNKNOWN"
    assert meds[0]["explicit_times"] == []


def test_prompt_asks_only_for_printed_clock_times():
    """The single most important prompt property of this redesign: the model
    must not be asked to derive reminder times at all. That derivation was
    qwen2.5:7b's ONLY measured held-out miss (2026-07-28), and it now lives
    in `rx_guardrails` as a lookup table instead."""
    assert "explicit_times" in rx_extract.PROMPT
    assert "specific_times" not in rx_extract.PROMPT
    assert "LITERALLY PRINTED" in rx_extract.PROMPT
    # No slot->time derivation table may survive in the prompt.
    for leaked in ("morning=08:00", 'ONCE_DAILY -> ["08:00"]', 'BID -> ["08:00","18:00"]'):
        assert leaked not in rx_extract.PROMPT
