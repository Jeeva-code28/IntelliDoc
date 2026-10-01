import os
import json
import logging
import hashlib
import pickle
import numpy as np
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("project_npn")


class RedisCache:
    """
    Production Redis Caching Layer.
    - Vector deduplication cache: vec:{content_hash} (24h TTL)
    - Serialized BM25 state cache: bm25:index:{tenant_id} (1h TTL)
    - Distributed Circuit Breaker state sync: circuit_breaker:{provider}
    Includes full in-memory fallback for local development when Redis server is offline.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._connect()

    def _connect(self) -> None:
        try:
            import redis
            client = redis.Redis.from_url(self.redis_url, decode_responses=False, socket_timeout=1.0)
            client.ping()
            self.redis_client = client
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection unavailable ({e}). Operating in resilient In-Memory Cache Fallback mode.")
            self.redis_client = None

    def get_vector(self, text_content: str) -> Optional[np.ndarray]:
        """Gets cached embedding vector by text content hash."""
        content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        key = f"vec:{content_hash}"
        
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return np.frombuffer(data, dtype=np.float32)
            except Exception as e:
                logger.debug(f"Redis get_vector error: {e}")

        # In-memory fallback
        if key in self._memory_cache:
            return self._memory_cache[key][0]
        return None

    def set_vector(self, text_content: str, vector: np.ndarray, ttl_seconds: int = 86400) -> None:
        """Caches embedding vector by text content hash (default TTL: 24 hours)."""
        content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        key = f"vec:{content_hash}"
        vec_bytes = vector.astype(np.float32).tobytes()

        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, vec_bytes)
                return
            except Exception as e:
                logger.debug(f"Redis set_vector error: {e}")

        # In-memory fallback
        self._memory_cache[key] = (vector.astype(np.float32), ttl_seconds)

    def get_bm25_state(self, tenant_id: str = "default_tenant") -> Optional[Any]:
        """Gets serialized BM25 index state."""
        key = f"bm25:index:{tenant_id}"
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
            except Exception as e:
                logger.debug(f"Redis get_bm25_state error: {e}")
        if key in self._memory_cache:
            return self._memory_cache[key][0]
        return None

    def set_bm25_state(self, state_obj: Any, tenant_id: str = "default_tenant", ttl_seconds: int = 3600) -> None:
        """Caches serialized BM25 index state (default TTL: 1 hour)."""
        key = f"bm25:index:{tenant_id}"
        serialized = pickle.dumps(state_obj)
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, serialized)
                return
            except Exception as e:
                logger.debug(f"Redis set_bm25_state error: {e}")
        self._memory_cache[key] = (state_obj, ttl_seconds)

    def get_circuit_breaker_state(self, provider: str) -> Optional[Dict[str, Any]]:
        """Gets circuit breaker status from Redis across cluster nodes."""
        key = f"circuit_breaker:{provider}"
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data.decode("utf-8"))
            except Exception as e:
                logger.debug(f"Redis get_circuit_breaker_state error: {e}")
        if key in self._memory_cache:
            return self._memory_cache[key][0]
        return None

    def set_circuit_breaker_state(self, provider: str, state_dict: Dict[str, Any], ttl_seconds: int = 300) -> None:
        """Stores circuit breaker status in Redis for distributed node synchronization."""
        key = f"circuit_breaker:{provider}"
        data = json.dumps(state_dict).encode("utf-8")
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, data)
                return
            except Exception as e:
                logger.debug(f"Redis set_circuit_breaker_state error: {e}")
        self._memory_cache[key] = (state_dict, ttl_seconds)


_redis_cache = None


def get_redis_cache() -> RedisCache:
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
