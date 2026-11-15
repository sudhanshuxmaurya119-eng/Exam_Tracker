"""Sliding-window rate limiting middleware and endpoint dependencies."""

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable, Deque, Dict
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter keyed by client IP and bucket."""

    def __init__(self) -> None:
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._requests[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - q[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            q.append(now)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_dependency(bucket: str, max_requests: int, window_seconds: int = 60) -> Callable:
    """Create a FastAPI dependency that enforces rate limits per client IP and bucket."""

    async def _limiter(request: Request) -> None:
        client_ip = get_client_ip(request)
        key = f"{bucket}:{client_ip}"
        rate_limiter.check(key=key, max_requests=max_requests, window_seconds=window_seconds)

    return _limiter
