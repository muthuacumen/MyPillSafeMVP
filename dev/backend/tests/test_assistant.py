"""POST /api/v1/assistant/{chat,voice} -- the public MyPillSafe Assistant
(project explainer, Phase 5). Mirrors test_qa.py's Claude-mocking idiom
(monkeypatching `cb4_service._get_client`, which `assistant_service.py`
reuses) so these tests never call a real Claude API or load a real
faster-whisper model.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.rate_limit import assistant_chat_limiter, assistant_voice_limiter
from app.services import assistant_kb, cb4_service, voice_transcribe


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """These limiters are module-level singletons shared across every test
    in this file -- reset before each test so one test's requests never
    trip another's 429."""
    assistant_chat_limiter.reset()
    assistant_voice_limiter.reset()
    yield
    assistant_chat_limiter.reset()
    assistant_voice_limiter.reset()


# --- Claude mocking (same shape as tests/test_qa.py) ------------------------


class _FakeTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeClaudeMessage:
    def __init__(self, text: str):
        self.content = [_FakeTextBlock(text)]


class _FakeClaudeMessages:
    def __init__(self, responses: list):
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


def _no_claude_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cb4_service, "_get_client", lambda: None)


# ---------------------------------------------------------------------------
# KB retrieval sanity
# ---------------------------------------------------------------------------

def test_kb_retrieve_exact_question_is_high_confidence():
    context, sources, confidence = assistant_kb.retrieve("What is MyPillSafe?")
    assert confidence >= assistant_kb.HIGH_CONFIDENCE_THRESHOLD
    assert sources[0]["question"] == "What is MyPillSafe?"
    assert "MyPillSafe" in context


def test_kb_retrieve_gibberish_is_low_confidence():
    _, _, confidence = assistant_kb.retrieve("blah gibberish xyzzy quux")
    assert confidence < assistant_kb.CLARIFICATION_THRESHOLD


def test_med_intent_gate_flags_dosing_and_interaction_questions():
    assert assistant_kb.is_medication_intent("can I take ibuprofen with warfarin?")
    assert assistant_kb.is_medication_intent("what is the dose of metformin")
    assert assistant_kb.is_medication_intent("are there side effects from acetaminophen")
    assert not assistant_kb.is_medication_intent("What is MyPillSafe?")
    assert not assistant_kb.is_medication_intent("Who built MyPillSafe?")


# ---------------------------------------------------------------------------
# Zone routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_high_confidence_zone_calls_llm(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    fake_client = _install_fake_claude(monkeypatch, ["MyPillSafe is a capstone medication-safety project."])

    resp = await client.post("/api/v1/assistant/chat", json={"query": "What is MyPillSafe?", "language": "en"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["used_llm"] is True
    assert body["confidence"] >= assistant_kb.HIGH_CONFIDENCE_THRESHOLD
    assert body["response"] == "MyPillSafe is a capstone medication-safety project."
    assert body["redirect_to_qa"] is False
    assert body["clarification_needed"] is False
    assert len(body["sources"]) > 0
    assert len(fake_client.messages.calls) == 1


@pytest.mark.asyncio
async def test_chat_high_confidence_llm_failure_falls_back_to_kb_answer(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _install_fake_claude(monkeypatch, [None])  # simulated Claude failure

    resp = await client.post("/api/v1/assistant/chat", json={"query": "What is MyPillSafe?", "language": "en"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["used_llm"] is False
    assert "MyPillSafe" in body["response"]  # served the top KB answer directly


@pytest.mark.asyncio
async def test_chat_high_confidence_no_key_falls_back_to_kb_answer(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    _no_claude_client(monkeypatch)

    resp = await client.post("/api/v1/assistant/chat", json={"query": "What is MyPillSafe?", "language": "en"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["used_llm"] is False
    assert body["response"]  # non-empty


@pytest.mark.asyncio
async def test_chat_clarification_zone_no_llm_call(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    fake_client = _install_fake_claude(monkeypatch, [])  # any .create() call is a test failure

    resp = await client.post("/api/v1/assistant/chat", json={"query": "tell me about safety", "language": "en"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["clarification_needed"] is True
    assert body["used_llm"] is False
    assert body["response"] == assistant_kb.CLARIFICATION_PROMPT_EN
    assert len(body["clarification_options"]) == 3
    assert len(fake_client.messages.calls) == 0


@pytest.mark.asyncio
async def test_chat_fallback_zone_out_of_scope(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    fake_client = _install_fake_claude(monkeypatch, [])

    resp = await client.post(
        "/api/v1/assistant/chat", json={"query": "blah gibberish xyzzy quux", "language": "en"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["clarification_needed"] is False
    assert body["used_llm"] is False
    assert body["response"] == assistant_kb.FALLBACK_EN
    assert len(fake_client.messages.calls) == 0


@pytest.mark.asyncio
async def test_chat_fallback_zone_french(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _install_fake_claude(monkeypatch, [])

    resp = await client.post(
        "/api/v1/assistant/chat", json={"query": "blah gibberish xyzzy quux", "language": "fr"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == assistant_kb.FALLBACK_FR
    assert body["language"] == "fr"


# ---------------------------------------------------------------------------
# Medication-intent redirect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_medication_intent_redirects_without_llm_call(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    fake_client = _install_fake_claude(monkeypatch, [])  # any call fails the test

    resp = await client.post(
        "/api/v1/assistant/chat",
        json={"query": "can I take ibuprofen with warfarin?", "language": "en"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["redirect_to_qa"] is True
    assert body["used_llm"] is False
    assert body["response"] == assistant_kb.MED_REDIRECT_EN
    assert len(fake_client.messages.calls) == 0


@pytest.mark.asyncio
async def test_chat_medication_intent_redirect_french(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _install_fake_claude(monkeypatch, [])

    resp = await client.post(
        "/api/v1/assistant/chat",
        json={"query": "quelle est la dose de metformine", "language": "fr"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["redirect_to_qa"] is True
    assert body["response"] == assistant_kb.MED_REDIRECT_FR


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_rate_limit_429_after_ten_requests(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    _install_fake_claude(monkeypatch, [])  # every request in this test lands in a no-LLM zone

    for _ in range(10):
        resp = await client.post(
            "/api/v1/assistant/chat", json={"query": "blah gibberish xyzzy quux", "language": "en"}
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/assistant/chat", json={"query": "blah gibberish xyzzy quux", "language": "en"}
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"]["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_voice_rate_limit_429_after_five_requests(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(voice_transcribe, "transcribe", lambda path, language=None: "hello")

    for _ in range(5):
        resp = await client.post(
            "/api/v1/assistant/voice",
            files={"audio": ("voice.wav", b"fake-audio-bytes", "audio/wav")},
            data={"language": "en"},
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/assistant/voice",
        files={"audio": ("voice.wav", b"fake-audio-bytes", "audio/wav")},
        data={"language": "en"},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Voice endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voice_happy_path_returns_transcript(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(voice_transcribe, "transcribe", lambda path, language=None: "what is my pill safe")

    resp = await client.post(
        "/api/v1/assistant/voice",
        files={"audio": ("voice.wav", b"fake-audio-bytes", "audio/wav")},
        data={"language": "en"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"text": "what is my pill safe"}


@pytest.mark.asyncio
async def test_voice_transcription_failure_returns_clean_500(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    def _boom(path, language=None):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(voice_transcribe, "transcribe", _boom)

    resp = await client.post(
        "/api/v1/assistant/voice",
        files={"audio": ("voice.wav", b"fake-audio-bytes", "audio/wav")},
        data={"language": "en"},
    )

    assert resp.status_code == 500
    assert resp.json()["detail"]["error"]["code"] == "TRANSCRIBE_FAILED"


@pytest.mark.asyncio
async def test_voice_missing_audio_field_is_422(client: AsyncClient):
    # FastAPI's own validation for a missing required multipart field.
    resp = await client.post("/api/v1/assistant/voice", data={"language": "en"})
    assert resp.status_code == 422
