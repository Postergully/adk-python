"""In-memory sliding window rate limiter for Finny V1."""
from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """10 queries/user/minute sliding window."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        cutoff = now - self._window

        # Prune old entries
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > cutoff
        ]

        if len(self._requests[user_id]) >= self._max:
            return False

        self._requests[user_id].append(now)
        return True

    def remaining(self, user_id: str) -> int:
        now = time.time()
        cutoff = now - self._window
        recent = [ts for ts in self._requests[user_id] if ts > cutoff]
        return max(0, self._max - len(recent))

    def cooldown_message(self, user_id: str) -> str:
        return (
            "You've reached the rate limit (10 queries/minute). "
            "Please wait a moment before trying again."
        )
