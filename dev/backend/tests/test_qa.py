"""POST /api/v1/qa/chat -- BB3 Q&A + CB4 voice (Phase 4). Mirrors
test_pill_v2.py's httpx-mocking idiom so these never talk to a real sidecar
or a real Claude API in CI. The Anthropic client is mocked at the
cb4_service._get_client() seam (a plain callable override), not by faking
the `anthropic` package itself.
"""
import json

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import cb4_service

CONTEXT_READY_PAYLOAD = {
    "status": "context_ready",
    "resolution": {"entities": ["warfarin"], "din_count": 16},
    "sources": [
        {
            "tag": "[DIN:2242680]",
            "section": "drug_interactions",
            "source": "product_monograph",
            "match_status": None,
            "score": 0.031,
            "rerank_score": None,
        }
    ],
    "tier": "pm",
    "disclaimer": "PillSafe is a decision-support tool, not medical advice. Always confirm with your pharmacist or doctor.",
    "offered_tags": ["[DIN:2242680]"],
    "packed_sources": "[DIN:2242680] (section: drug_interactions)\nAvoid vitamin K rich foods.",
    "question": "what foods should I avoid with warfarin",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "sources_used": {"type": "array", "items": {"type": "string", "enum": ["[DIN:2242680]"]}},
            "abstained": {"type": "boolean"},
        },
        "required": ["answer", "sources_used", "abstained"],
    },
    "entity_names": ["warfarin"],
}

NOT_FOUND_PAYLOAD = {
    "status": "not_found",
    "resolution": {"entities": [], "din_count": 0},
    "abstained": True,
    "answer": "I couldn't find that medication in the Canadian formulary -- please check the "
    "spelling, give the ingredient name, or the DIN from the package.",
    "sources": [],
    "tier": "none",
    "disclaimer": "PillSafe is a decision-support tool, not medical advice. Always confirm with your pharmacist or doctor.",
    "cited_tags": [],
    "priority": 0.0,
    "latency_s": 0.01,
    "refused_dosing": False,
    "voice": "none",
}

FULL_MODE_PAYLOAD = {
    "status": "answered",
    "resolution": {"entities": ["warfarin"], "din_count": 16},
    "abstained": False,
    "answer": "Avoid vitamin K rich foods while taking warfarin.",
    "sources": [],
    "tier": "pm",
    "disclaimer": "PillSafe is a decision-support tool, not medical advice. Always confirm with your pharmacist or doctor.",
    "cited_tags": ["[DIN:2242680]"],
    "priority": 0.0,
    "guard_flags": {
        "json_degenerate_retried": False,
        "entity_guard_retried": False,
        "ingredient_consistency_retried": False,
        "guard_refused": False,
        "structural_inconsistency": False,
    },
    "latency_s": 4.1,
    "refused_dosing": False,
    "voice": "local_7b",
}


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]


class _FakeSidecarClient:
    """Stands in for httpx.AsyncClient for BOTH the sidecar's /qa/chat call
    (routes/qa.py) and its /qa/guard call (cb4_service._check_guards) --
    both modules `import httpx` and call `httpx.AsyncClient(...)`, so one
    monkeypatch of `httpx.AsyncClient` covers both."""

    chat_response_body: dict = NOT_FOUND_PAYLOAD
    chat_status_code: int = 200
    guard_responses: list = []  # queue popped one-per-call; class-level default rebound per test
    last_chat_kwargs: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        if url.endswith("/qa/chat"):
            _FakeSidecarClient.last_chat_kwargs = kwargs
            return _FakeResponse(_FakeSidecarClient.chat_status_code, _FakeSidecarClient.chat_response_body)
        if url.endswith("/qa/guard"):
            if _FakeSidecarClient.guard_responses:
                body = _FakeSidecarClient.guard_responses.pop(0)
            else:
                body = {"entity_violation": None, "ingredient_violation": None, "structural_inconsistency": False}
            return _FakeResponse(200, body)
        raise AssertionError(f"unexpected sidecar URL in test: {url}")


class _FakeTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeClaudeMessage:
    def __init__(self, text: str):
        self.content = [_FakeTextBlock(text)]


class _FakeClaudeMessages:
    def __init__(self, responses: list):
        # Each entry is either a JSON string (successful reply) or None
        # (simulated failure -- _call_claude's except-block returns None).
        self._responses = list(responses)
        self.calls: list = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("test queued fewer fake Claude responses than were consumed")
        nxt = self._responses.pop(0)
        if nxt is None:
            raise RuntimeError("simulated Claude API failure")
        return _FakeClaudeMessage(nxt)


class _FakeClaudeClient:
    def __init__(self, responses: list):
        self.messages = _FakeClaudeMessages(responses)


def _install_fake_claude(monkeypatch: pytest.MonkeyPatch, responses: list) -> _FakeClaudeClient:
    fake = _FakeClaudeClient(responses)
    monkeypatch.setattr(cb4_service, "_get_client", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_qa_chat_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/qa/chat", json={"message": "what foods should I avoid with warfarin"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_qa_chat_no_key_uses_offline_fallback(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    """No LLM_API_KEY configured -> sidecar mode="full" passthrough, voice="local_7b"."""
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    _FakeSidecarClient.chat_response_body = FULL_MODE_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "what foods should I avoid with warfarin"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["voice"] == "local_7b"
    assert body["status"] == "answered"
    assert body["answer"] == FULL_MODE_PAYLOAD["answer"]
    assert _FakeSidecarClient.last_chat_kwargs["json"]["mode"] == "full"


@pytest.mark.asyncio
async def test_qa_chat_context_ready_cb4_happy_path(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _FakeSidecarClient.chat_response_body = CONTEXT_READY_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    _FakeSidecarClient.guard_responses = []  # every /qa/guard call returns "no violation" (default)
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    claude_answer = json.dumps(
        {
            "answer": "Avoid vitamin K rich foods while taking warfarin.",
            "sources_used": ["[DIN:2242680]"],
            "abstained": False,
        }
    )
    fake_client = _install_fake_claude(monkeypatch, [claude_answer])

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "what foods should I avoid with warfarin"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "answered"
    assert body["voice"] == "cb4"
    assert body["model"] == settings.LLM_MODEL
    assert body["answer"] == "Avoid vitamin K rich foods while taking warfarin."
    assert body["cited_tags"] == ["[DIN:2242680]"]
    assert body["abstained"] is False
    assert body["refused_dosing"] is False
    assert body["disclaimer"] == CONTEXT_READY_PAYLOAD["disclaimer"]
    assert len(fake_client.messages.calls) == 1


@pytest.mark.asyncio
async def test_qa_chat_guard_violation_then_corrective_retry_cleans(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _FakeSidecarClient.chat_response_body = CONTEXT_READY_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    _FakeSidecarClient.guard_responses = [
        {"entity_violation": "ibuprofen", "ingredient_violation": None, "structural_inconsistency": False},  # entity check on draft 1
        {"entity_violation": None, "ingredient_violation": None, "structural_inconsistency": False},  # recheck on the retry -> clean
        {"entity_violation": None, "ingredient_violation": None, "structural_inconsistency": False},  # ingredient check
        {"entity_violation": None, "ingredient_violation": None, "structural_inconsistency": False},  # final structural check
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    bad_draft = json.dumps(
        {"answer": "Ibuprofen interacts with warfarin.", "sources_used": ["[DIN:2242680]"], "abstained": False}
    )
    clean_retry = json.dumps(
        {"answer": "Avoid vitamin K rich foods while taking warfarin.", "sources_used": ["[DIN:2242680]"], "abstained": False}
    )
    fake_client = _install_fake_claude(monkeypatch, [bad_draft, clean_retry])

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "what foods should I avoid with warfarin"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "answered"
    assert body["answer"] == "Avoid vitamin K rich foods while taking warfarin."
    assert body["guard_flags"]["entity_guard_retried"] is True
    assert body["guard_flags"]["guard_refused"] is False
    assert len(fake_client.messages.calls) == 2
    # the corrective retry's prompt names the offending term
    assert "ibuprofen" in fake_client.messages.calls[1]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_qa_chat_guard_violation_twice_refuses(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _FakeSidecarClient.chat_response_body = CONTEXT_READY_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    _FakeSidecarClient.guard_responses = [
        {"entity_violation": "ibuprofen", "ingredient_violation": None, "structural_inconsistency": False},
        {"entity_violation": "ibuprofen", "ingredient_violation": None, "structural_inconsistency": False},  # still violating after retry
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    bad_draft = json.dumps(
        {"answer": "Ibuprofen interacts with warfarin.", "sources_used": ["[DIN:2242680]"], "abstained": False}
    )
    still_bad = json.dumps(
        {"answer": "Ibuprofen is still mentioned here.", "sources_used": ["[DIN:2242680]"], "abstained": False}
    )
    fake_client = _install_fake_claude(monkeypatch, [bad_draft, still_bad])

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "what foods should I avoid with warfarin"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "guard_refused"
    assert body["answer"] == "I couldn't produce a reliable answer for this -- please ask your pharmacist."
    assert body["abstained"] is True
    assert body["cited_tags"] == []
    assert body["guard_flags"]["guard_refused"] is True
    assert len(fake_client.messages.calls) == 2


@pytest.mark.asyncio
async def test_qa_chat_json_degeneracy_retries_then_succeeds(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _FakeSidecarClient.chat_response_body = CONTEXT_READY_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    _FakeSidecarClient.guard_responses = []  # all clean
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    clean_answer = json.dumps(
        {"answer": "Avoid vitamin K rich foods while taking warfarin.", "sources_used": ["[DIN:2242680]"], "abstained": False}
    )
    # First call raises (simulated failure -> _call_claude returns None -> _empty() -> retried).
    fake_client = _install_fake_claude(monkeypatch, [None, clean_answer])

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "what foods should I avoid with warfarin"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "answered"
    assert body["answer"] == "Avoid vitamin K rich foods while taking warfarin."
    assert body["guard_flags"]["json_degenerate_retried"] is True
    assert len(fake_client.messages.calls) == 2


@pytest.mark.asyncio
async def test_qa_chat_non_generation_status_passes_through_verbatim(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _FakeSidecarClient.chat_response_body = NOT_FOUND_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)
    # No Claude client installed -- if the route tried to call CB4 for a
    # non-context_ready status, cb4_service._get_client() would return None
    # (no monkeypatch) and answer_question() would raise.

    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "can I take Coumadin with food"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "not_found"
    assert body["voice"] == "none"
    assert body["answer"] == NOT_FOUND_PAYLOAD["answer"]
    assert body["resolution"] == NOT_FOUND_PAYLOAD["resolution"]


@pytest.mark.asyncio
async def test_qa_chat_din_bypass_converted_to_sb2_token(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")  # exercise the boundary conversion via full mode
    _FakeSidecarClient.chat_response_body = FULL_MODE_PAYLOAD
    _FakeSidecarClient.chat_status_code = 200
    monkeypatch.setattr(httpx, "AsyncClient", _FakeSidecarClient)

    resp = await client.post(
        "/api/v1/qa/chat",
        headers=auth_headers,
        json={"message": "what foods should I avoid with warfarin", "din": "00013803"},
    )

    assert resp.status_code == 200
    assert _FakeSidecarClient.last_chat_kwargs["json"]["din"] == "DIN13803"


@pytest.mark.asyncio
async def test_qa_chat_invalid_din_returns_422(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/qa/chat", headers=auth_headers, json={"message": "warfarin question", "din": "not-a-din"}
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"]["code"] == "INVALID_DIN"
