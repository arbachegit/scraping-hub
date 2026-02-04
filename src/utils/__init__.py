"""
Scraping Hub - Utils
Utilitarios compartilhados
"""

from .cache import cache_result, clear_cache
from .rate_limiter import RateLimiter

__all__ = ["cache_result", "clear_cache", "RateLimiter"]
