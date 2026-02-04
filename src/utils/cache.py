"""
Cache Utils
Sistema de cache em memoria com TTL
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import structlog
from cachetools import TTLCache

from config.settings import settings

logger = structlog.get_logger()

# Cache global
_cache = TTLCache(
    maxsize=settings.cache_max_size,
    ttl=settings.cache_ttl
)

# Estatisticas
_stats = {
    "hits": 0,
    "misses": 0,
    "sets": 0
}


def _make_key(*args, **kwargs) -> str:
    """Gera chave de cache a partir dos argumentos"""
    key_data = json.dumps(
        {"args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str
    )
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_result(
    ttl: Optional[int] = None,
    prefix: str = ""
) -> Callable:
    """
    Decorator para cachear resultado de funcao

    Args:
        ttl: Time-to-live em segundos (usa default se None)
        prefix: Prefixo para a chave de cache

    Usage:
        @cache_result(ttl=300, prefix="empresa")
        async def get_empresa(cnpj: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Gerar chave
            key = f"{prefix}:{func.__name__}:{_make_key(*args, **kwargs)}"

            # Verificar cache
            if key in _cache:
                _stats["hits"] += 1
                logger.debug("cache_hit", key=key)
                return _cache[key]

            _stats["misses"] += 1

            # Executar funcao
            result = await func(*args, **kwargs)

            # Armazenar no cache
            if result is not None:
                _cache[key] = result
                _stats["sets"] += 1
                logger.debug("cache_set", key=key)

            return result

        return wrapper
    return decorator


def get_cached(key: str) -> Optional[Any]:
    """Obtem valor do cache"""
    return _cache.get(key)


def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Define valor no cache"""
    _cache[key] = value
    _stats["sets"] += 1


def delete_cached(key: str) -> bool:
    """Remove valor do cache"""
    try:
        del _cache[key]
        return True
    except KeyError:
        return False


def clear_cache() -> int:
    """Limpa todo o cache"""
    count = len(_cache)
    _cache.clear()
    logger.info("cache_cleared", items=count)
    return count


def get_cache_stats() -> dict:
    """Retorna estatisticas do cache"""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total * 100) if total > 0 else 0

    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "sets": _stats["sets"],
        "hit_rate": round(hit_rate, 2),
        "current_size": len(_cache),
        "max_size": _cache.maxsize,
        "ttl": _cache.ttl
    }


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Gera chave de cache manualmente"""
    return f"{prefix}:{_make_key(*args, **kwargs)}"
