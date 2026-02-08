import time
from collections import defaultdict
from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = time.time()
        self._cleanup_interval: float = 300.0  # purge stale keys every 5 min

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds
        stale = [uid for uid, ts in self._requests.items() if not ts or ts[-1] <= cutoff]
        for uid in stale:
            del self._requests[uid]

    def check(self, user_id: str) -> None:
        now = time.time()
        self._maybe_cleanup(now)
        cutoff = now - self.window_seconds
        # Remove expired entries
        self._requests[user_id] = [t for t in self._requests[user_id] if t > cutoff]
        if len(self._requests[user_id]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per minute.",
            )
        self._requests[user_id].append(now)


chat_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
