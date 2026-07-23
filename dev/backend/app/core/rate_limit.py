"""Small in-process sliding-window rate limiter (Phase 5).

`slowapi` was evaluated for the MyPillSafe Assistant's public, no-auth
endpoints (`POST /api/v1/assistant/chat` 10/min/IP, `/assistant/voice`
5/min/IP) and skipped in favour of this ~20-line dependency: it needs no
new package, no app.state wiring, and is trivially unit-testable by calling
`SlidingWindowLimiter.check()` directly with an explicit clock.

Deliberately single-process (in-memory) -- fine for this dev/demo
deployment; a multi-worker/multi-instance deployment would need a shared
store (e.g. Redis) instead, out of scope for this phase.

429s use the app's standard error envelope
(`{"detail": {"error": {"code": ..., "message": ...}}}`).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    """Allows at most `max_requests` calls to `check()` for a given key
    within any trailing `window_seconds` window."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> bool:
        """Returns True (and records the hit) if `key` is under its limit;
        False if it has already used up its budget in the current window."""
        now = time.monotonic() if now is None else now
        bucket = self._hits[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def reset(self) -> None:
        """Test helper -- clears all recorded hits (avoids cross-test
        pollution of this module-level singleton's shared state)."""
        self._hits.clear()


def _client_key(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit_dependency(limiter: SlidingWindowLimiter):
    """Builds a FastAPI dependency that enforces `limiter` keyed by client IP."""

    async def _check(request: Request) -> None:
        if not limiter.check(_client_key(request)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests — please wait a moment and try again.",
                    }
                },
            )

    return _check


# Shared singletons used by app/api/v1/routes/assistant.py.
assistant_chat_limiter = SlidingWindowLimiter(max_requests=10, window_seconds=60.0)
assistant_voice_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60.0)
