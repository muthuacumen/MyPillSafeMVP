"""MyPillSafe Assistant -- voice input transcription (Phase 5).

`POST /api/v1/assistant/voice` accepts a short audio clip and transcribes it
with faster-whisper's "base" model, CPU + int8 (no GPU needed for a few
seconds of speech; keeps this off the RTX 4060 the brains sidecar's vision
models already use -- see the Builder Briefing's two-process / GPU
constraints). The model is a lazy singleton: the first call in a process
pays the load cost, every call after is fast.

This is a plain function module (not a class) so tests can monkeypatch
`transcribe` directly, mirroring how `tests/test_qa.py` monkeypatches
`cb4_service._get_client` -- no real model load happens in CI.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_model: Any = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info("Loading faster-whisper 'base' model (CPU, int8) -- first call only.")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(file_path: str, language: str | None = None) -> str:
    """Transcribes the audio file at `file_path`. `language` should be "en"
    or "fr" (anything else lets Whisper auto-detect)."""
    model = _get_model()
    lang = language if language in ("en", "fr") else None
    segments, _info = model.transcribe(file_path, language=lang)
    return " ".join(segment.text.strip() for segment in segments).strip()
