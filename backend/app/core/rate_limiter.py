"""Redis-based API rate limiter middleware.

Implements a sliding window rate limit per user (by JWT sub claim).
Configurable limits per endpoint group.
"""

import time
import structlog
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import redis.asyncio as aioredis

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Rate limit configuration: (requests, window_seconds)
RATE_LIMITS = {
    "pipeline": (30, 3600),     # 30 pipeline runs per hour
    "generate": (60, 3600),     # 60 document generations per hour
    "search": (120, 60),        # 120 searches per minute
    "default": (300, 60),       # 300 requests per minute for general API
}

# Map URL patterns to rate limit groups
URL_GROUPS = [
    ("/run-pipeline", "pipeline"),
    ("/run-stage", "pipeline"),
    ("/compare-schemes", "generate"),
    ("/generate", "generate"),
    ("/export-excel", "generate"),
    ("/search", "search"),
]


def _get_group(path: str) -> str:
    for pattern, group in URL_GROUPS:
        if pattern in path:
            return group
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis sorted sets."""

    def __init__(self, app, redis_url: str | None = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url, decode_responses=True, max_connections=5,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip health check
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        # Extract user identifier
        user_id = self._extract_user_id(request)
        if not user_id:
            return await call_next(request)  # No auth = no rate limit (auth middleware handles it)

        # Determine rate limit group
        group = _get_group(request.url.path)
        max_requests, window = RATE_LIMITS.get(group, RATE_LIMITS["default"])

        # Check rate limit
        allowed, remaining, retry_after = await self._check_limit(
            user_id, group, max_requests, window
        )

        if not allowed:
            logger.warning(
                "rate_limited",
                user_id=user_id,
                group=group,
                path=request.url.path,
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                    "Retry-After": str(retry_after),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    async def _check_limit(
        self, user_id: str, group: str, max_requests: int, window: int
    ) -> tuple[bool, int, int]:
        """Check and update rate limit counter.

        Returns:
            (allowed, remaining, retry_after_seconds)
        """
        r = await self._get_redis()
        if not r:
            return True, max_requests, 0  # Redis unavailable = allow all

        now = time.time()
        key = f"ratelimit:{group}:{user_id}"

        try:
            pipe = r.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(key, 0, now - window)
            # Count current entries
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Set expiry
            pipe.expire(key, window)

            results = await pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                # Get the oldest entry to calculate retry_after
                oldest = await r.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now) + 1
                else:
                    retry_after = window
                return False, 0, retry_after

            remaining = max_requests - current_count - 1
            return True, max(remaining, 0), 0

        except Exception as e:
            logger.warning("rate_limit_check_error", error=str(e))
            return True, max_requests, 0

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return None

        token = auth[7:]
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(token)
            return payload.get("sub")
        except Exception:
            return None
