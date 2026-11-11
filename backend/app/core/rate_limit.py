import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import Request, status
from app.core.exceptions import AppException


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter for protecting sensitive auth endpoints.
    Tracks request timestamps per client IP.
    """

    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Purge timestamps outside of current sliding window
            timestamps = [t for t in self._requests[key] if t > cutoff]
            if len(timestamps) >= max_requests:
                self._requests[key] = timestamps
                return False

            timestamps.append(now)
            self._requests[key] = timestamps
            return True


# Global rate limiter instance
_limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    FastAPI dependency enforcing rate limits per client IP on sensitive routes.
    Example: Depends(rate_limit(max_requests=5, window_seconds=60))
    """
    async def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"

        if not _limiter.check_rate_limit(key, max_requests, window_seconds):
            raise AppException(
                message=f"Too many requests to {endpoint}. Please wait {window_seconds} seconds before trying again.",
                code="RATE_LIMIT_EXCEEDED",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                details={"retry_after_seconds": window_seconds},
            )

    return dependency
