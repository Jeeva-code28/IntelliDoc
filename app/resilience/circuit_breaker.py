import time
import random
from typing import Dict, Any, Tuple, Optional


class ProviderCircuitBreaker:
    """
    LLM Provider Circuit Breaker and Failover Manager.
    State machine: CLOSED (healthy) -> OPEN (tripped on failures) -> HALF-OPEN (recovery test).
    Rules:
      - 3 failures within 60s trips circuit to OPEN for 300s (5 minutes).
      - Forces fallback to alternate providers (Groq, OpenAI, Ollama).
      - Exponential backoff with jitter: min(0.5 * 2^attempt + jitter, 30.0)
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 300.0, window_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.window_seconds = window_seconds

        # Provider state tracking: {provider_name: {"failures": [timestamps], "state": "CLOSED", "tripped_at": 0.0}}
        self.providers: Dict[str, Dict[str, Any]] = {}
        for p in ["gemini", "groq", "openai", "ollama"]:
            self.providers[p] = {
                "failures": [],
                "state": "CLOSED",
                "tripped_at": 0.0,
                "total_calls": 0,
                "successful_calls": 0
            }

    def can_call(self, provider: str) -> bool:
        prov = provider.lower()
        if prov not in self.providers:
            return True

        p_info = self.providers[prov]
        now = time.time()

        # Check Redis distributed state first
        try:
            from app.cache.redis_cache import get_redis_cache
            cache = get_redis_cache()
            remote_state = cache.get_circuit_breaker_state(prov)
            if remote_state and remote_state.get("state") == "OPEN":
                tripped_at = remote_state.get("tripped_at", 0.0)
                if now - tripped_at < self.reset_timeout_seconds:
                    return False
        except Exception:
            pass

        if p_info["state"] == "OPEN":
            if now - p_info["tripped_at"] >= self.reset_timeout_seconds:
                p_info["state"] = "HALF-OPEN"
                return True
            return False

        return True

    def record_success(self, provider: str):
        prov = provider.lower()
        if prov in self.providers:
            p_info = self.providers[prov]
            p_info["successful_calls"] += 1
            p_info["total_calls"] += 1
            p_info["failures"].clear()
            p_info["state"] = "CLOSED"
            try:
                from app.cache.redis_cache import get_redis_cache
                get_redis_cache().set_circuit_breaker_state(prov, {"state": "CLOSED", "tripped_at": 0.0})
            except Exception:
                pass

    def record_failure(self, provider: str):
        prov = provider.lower()
        if prov in self.providers:
            now = time.time()
            p_info = self.providers[prov]
            p_info["total_calls"] += 1
            # Clean old failures outside 60s window
            p_info["failures"] = [t for t in p_info["failures"] if now - t <= self.window_seconds]
            p_info["failures"].append(now)

            if len(p_info["failures"]) >= self.failure_threshold:
                p_info["state"] = "OPEN"
                p_info["tripped_at"] = now
                try:
                    from app.cache.redis_cache import get_redis_cache
                    get_redis_cache().set_circuit_breaker_state(prov, {"state": "OPEN", "tripped_at": now}, ttl_seconds=int(self.reset_timeout_seconds))
                except Exception:
                    pass

    def reset(self, provider: Optional[str] = None):
        """
        Resets circuit state to CLOSED and clears failure history.
        If provider is specified, resets only that provider; otherwise resets all providers.
        """
        targets = [provider.lower()] if provider else list(self.providers.keys())
        for p in targets:
            if p in self.providers:
                self.providers[p]["failures"].clear()
                self.providers[p]["state"] = "CLOSED"
                self.providers[p]["tripped_at"] = 0.0
                try:
                    from app.cache.redis_cache import get_redis_cache
                    get_redis_cache().set_circuit_breaker_state(p, {"state": "CLOSED", "tripped_at": 0.0})
                except Exception:
                    pass

    def calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter: 0.5s, 1s, 2s, 4s up to max 30s."""
        base = min(30.0, 0.5 * (2 ** attempt))
        jitter = random.uniform(0.0, 0.2 * base)
        return base + jitter

    def get_status(self) -> Dict[str, Any]:
        """Returns provider health status for /health endpoint."""
        now = time.time()
        status = {}
        for name, info in self.providers.items():
            state = info["state"]
            if state == "OPEN" and (now - info["tripped_at"] >= self.reset_timeout_seconds):
                state = "HALF-OPEN"
            status[name] = {
                "state": state,
                "recent_failures_60s": len([t for t in info["failures"] if now - t <= self.window_seconds]),
                "total_calls": info["total_calls"],
                "successful_calls": info["successful_calls"]
            }
        return status


# Singleton instance
_circuit_breaker = None


def get_circuit_breaker() -> ProviderCircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = ProviderCircuitBreaker()
    return _circuit_breaker
