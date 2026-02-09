"""
IconsAI Scraping - Utils
Utilitarios compartilhados
"""

from .cache import cache_result, clear_cache
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
)
from .rate_limiter import RateLimiter

__all__ = [
    # Cache
    "cache_result",
    "clear_cache",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    "get_circuit_breaker",
    # Rate Limiter
    "RateLimiter",
]
