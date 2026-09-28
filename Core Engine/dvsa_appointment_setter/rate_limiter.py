from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self,
        poll_seconds: int,
        jitter_seconds: int = 0,
        error_backoff_seconds: int = 300,
        rate_limit_cooldown_seconds: int = 3600,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.poll_seconds = max(60, int(poll_seconds))
        self.jitter_seconds = max(0, int(jitter_seconds))
        self.error_backoff_seconds = max(self.poll_seconds, int(error_backoff_seconds))
        self.rate_limit_cooldown_seconds = max(
            self.error_backoff_seconds, int(rate_limit_cooldown_seconds)
        )
        self._clock = clock or time.monotonic
        self._next_allowed_at = self._clock()
        self._failure_count = 0

    def seconds_until_next_slot(self) -> float:
        return max(0.0, self._next_allowed_at - self._clock())

    async def wait_for_slot(self) -> float:
        wait_seconds = self.seconds_until_next_slot()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        return wait_seconds

    def mark_check_complete(self, had_error: bool = False) -> float:
        if had_error:
            self._failure_count = min(self._failure_count + 1, 4)
        else:
            self._failure_count = 0

        delay = self.poll_seconds + self._jitter()
        if had_error:
            delay = max(delay, self.error_backoff_seconds * self._failure_count)

        self._next_allowed_at = self._clock() + delay
        return delay

    def mark_rate_limited(self) -> float:
        self._failure_count = 0
        delay = self.rate_limit_cooldown_seconds + self._jitter()
        self._next_allowed_at = self._clock() + delay
        return delay

    def _jitter(self) -> float:
        if self.jitter_seconds <= 0:
            return 0.0
        return random.uniform(0, self.jitter_seconds)


def format_wait(seconds: float) -> str:
    whole_seconds = max(0, int(round(seconds)))
    minutes, remainder = divmod(whole_seconds, 60)
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"
