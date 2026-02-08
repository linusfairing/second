import logging
import time
from collections import defaultdict

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback (single-process only)
# ---------------------------------------------------------------------------


class InMemoryRateLimiter:
    """Sliding-window rate limiter using local memory.

    Works correctly for single-process deployments only.  With multiple
    workers each process keeps its own counters, effectively multiplying
    the allowed rate by the number of workers.
    """

    def __init__(self, max_requests: int, window_seconds: int, name: str = ""):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = time.time()
        self._cleanup_interval: float = 300.0

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds
        stale = [uid for uid, ts in self._requests.items() if not ts or ts[-1] <= cutoff]
        for uid in stale:
            del self._requests[uid]

    def check(self, key: str) -> None:
        now = time.time()
        self._maybe_cleanup(now)
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per minute.",
            )
        self._requests[key].append(now)


# ---------------------------------------------------------------------------
# Redis-backed sliding window (works across workers)
# ---------------------------------------------------------------------------


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets.

    Each request is stored as a member with its timestamp as the score.
    On each check we:
      1. Remove entries outside the window.
      2. Count remaining entries.
      3. If under the limit, add the new entry.
    All three steps run in a single pipeline (atomic round-trip).
    """

    def __init__(self, redis_client, max_requests: int, window_seconds: int, name: str = ""):
        self._redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name

    def check(self, key: str) -> None:
        now = time.time()
        redis_key = f"ratelimit:{self.name}:{key}"
        cutoff = now - self.window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {f"{now}": now})
        pipe.expire(redis_key, self.window_seconds + 1)
        results = pipe.execute()

        current_count = results[1]  # zcard result (before the zadd)
        if current_count >= self.max_requests:
            # Remove the entry we just added since we're over the limit
            pipe2 = self._redis.pipeline()
            pipe2.zrem(redis_key, f"{now}")
            pipe2.execute()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per minute.",
            )


# ---------------------------------------------------------------------------
# Factory — tries Redis, falls back to in-memory
# ---------------------------------------------------------------------------

_redis_client = None
_redis_available: bool | None = None  # None = not yet checked


def _get_redis_client():
    """Lazily connect to Redis.  Returns the client or None."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client

    from app.config import settings

    if not settings.REDIS_URL:
        _redis_available = False
        return None

    try:
        import redis

        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected for rate limiting: %s", settings.REDIS_URL)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable (%s), falling back to in-memory rate limiting", exc)
        _redis_available = False
        return None


def create_rate_limiter(max_requests: int, window_seconds: int, name: str = ""):
    """Create a rate limiter — Redis-backed if available, in-memory otherwise."""
    client = _get_redis_client()
    if client is not None:
        return RedisRateLimiter(client, max_requests, window_seconds, name)
    return InMemoryRateLimiter(max_requests, window_seconds, name)


# Pre-built limiters used by routers
chat_rate_limiter = create_rate_limiter(max_requests=30, window_seconds=60, name="chat")
auth_rate_limiter = create_rate_limiter(max_requests=10, window_seconds=60, name="auth")
message_rate_limiter = create_rate_limiter(max_requests=60, window_seconds=60, name="msg")
