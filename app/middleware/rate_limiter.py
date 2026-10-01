import time
import logging
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.cache.redis_cache import get_redis_cache

logger = logging.getLogger("project_npn")


class RateLimiter:
    """
    Sliding window rate limiter per tenant.
    - Free Tier: 100 requests / minute
    - Enterprise Tier: 10,000 requests / minute
    Uses Redis zset when available, with in-memory sliding window fallback.
    """

    TIER_LIMITS = {
        "free": 100,
        "standard": 1000,
        "enterprise": 10000
    }

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._memory_windows: Dict[str, List[float]] = {}

    def is_allowed(self, tenant_id: str = "default_tenant", tier: str = "free") -> Tuple[bool, int, int]:
        """
        Checks if request is allowed under sliding window limit.
        Returns: (is_allowed, remaining_quota, limit)
        """
        limit = self.TIER_LIMITS.get(tier.lower(), 100)
        now = time.time()
        cutoff = now - self.window_seconds
        cache = get_redis_cache()

        if cache.redis_client:
            try:
                key = f"rate_limit:{tenant_id}"
                pipe = cache.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.window_seconds + 5)
                results = pipe.execute()
                current_count = results[1]

                if current_count >= limit:
                    return False, 0, limit
                return True, max(0, limit - current_count - 1), limit
            except Exception as e:
                logger.debug(f"Redis rate limiter error: {e}")

        # In-memory sliding window fallback
        if tenant_id not in self._memory_windows:
            self._memory_windows[tenant_id] = []

        timestamps = [t for t in self._memory_windows[tenant_id] if t > cutoff]
        self._memory_windows[tenant_id] = timestamps

        if len(timestamps) >= limit:
            return False, 0, limit

        self._memory_windows[tenant_id].append(now)
        return True, limit - len(self._memory_windows[tenant_id]), limit


_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude health and metrics endpoints from rate limiting
        if request.url.path in ["/health", "/metrics", "/"]:
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID", "default_tenant")
        tier = request.headers.get("X-Tenant-Tier", "free")

        allowed, remaining, limit = _rate_limiter.is_allowed(tenant_id, tier)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for tenant '{tenant_id}'. Limit: {limit} req/min."
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
