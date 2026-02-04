"""
Rate Limiter
Controle de taxa de requisicoes
"""

import structlog
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque

from config.settings import settings


logger = structlog.get_logger()


@dataclass
class RateLimitConfig:
    """Configuracao de rate limit"""
    requests: int
    period: int  # segundos
    burst: Optional[int] = None


# Configuracoes por provider
DEFAULT_LIMITS = {
    "coresignal": RateLimitConfig(
        requests=settings.coresignal_rate_limit,
        period=settings.rate_limit_period
    ),
    "proxycurl": RateLimitConfig(
        requests=settings.proxycurl_rate_limit,
        period=settings.rate_limit_period
    ),
    "firecrawl": RateLimitConfig(
        requests=settings.firecrawl_rate_limit,
        period=settings.rate_limit_period
    )
}


@dataclass
class RateLimiterState:
    """Estado do rate limiter"""
    requests: deque = field(default_factory=deque)
    blocked_until: Optional[datetime] = None


class RateLimiter:
    """
    Rate limiter com sliding window

    Controla o numero de requisicoes por periodo de tempo
    usando uma janela deslizante.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        requests: Optional[int] = None,
        period: Optional[int] = None
    ):
        """
        Inicializa rate limiter

        Args:
            provider: Nome do provider (usa config padrao)
            requests: Numero de requisicoes permitidas
            period: Periodo em segundos
        """
        if provider and provider in DEFAULT_LIMITS:
            config = DEFAULT_LIMITS[provider]
            self.max_requests = requests or config.requests
            self.period = period or config.period
        else:
            self.max_requests = requests or 100
            self.period = period or 60

        self.provider = provider or "default"
        self._state = RateLimiterState()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Adquire permissao para fazer requisicao

        Returns:
            True se permitido, False se bloqueado
        """
        async with self._lock:
            now = datetime.utcnow()

            # Verificar se esta bloqueado
            if self._state.blocked_until and now < self._state.blocked_until:
                wait_time = (self._state.blocked_until - now).total_seconds()
                logger.warning(
                    "rate_limited",
                    provider=self.provider,
                    wait_seconds=wait_time
                )
                return False

            # Limpar requests antigas
            cutoff = now - timedelta(seconds=self.period)
            while (
                self._state.requests and
                self._state.requests[0] < cutoff
            ):
                self._state.requests.popleft()

            # Verificar limite
            if len(self._state.requests) >= self.max_requests:
                # Calcular tempo de espera
                oldest = self._state.requests[0]
                wait_until = oldest + timedelta(seconds=self.period)
                self._state.blocked_until = wait_until

                wait_time = (wait_until - now).total_seconds()
                logger.warning(
                    "rate_limit_reached",
                    provider=self.provider,
                    current=len(self._state.requests),
                    max=self.max_requests,
                    wait_seconds=wait_time
                )
                return False

            # Registrar request
            self._state.requests.append(now)
            self._state.blocked_until = None

            return True

    async def wait(self) -> None:
        """
        Aguarda ate ter permissao para fazer requisicao

        Bloqueia ate que o rate limit permita nova requisicao
        """
        while not await self.acquire():
            async with self._lock:
                if self._state.blocked_until:
                    now = datetime.utcnow()
                    wait_time = max(
                        0,
                        (self._state.blocked_until - now).total_seconds()
                    )
                else:
                    wait_time = 1

            logger.debug(
                "rate_limit_waiting",
                provider=self.provider,
                seconds=wait_time
            )
            await asyncio.sleep(wait_time + 0.1)

    def get_stats(self) -> Dict:
        """Retorna estatisticas do rate limiter"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.period)

        # Contar requests no periodo atual
        current_requests = sum(
            1 for r in self._state.requests if r >= cutoff
        )

        return {
            "provider": self.provider,
            "max_requests": self.max_requests,
            "period_seconds": self.period,
            "current_requests": current_requests,
            "remaining": max(0, self.max_requests - current_requests),
            "is_blocked": (
                self._state.blocked_until is not None and
                now < self._state.blocked_until
            )
        }

    def reset(self) -> None:
        """Reseta o estado do rate limiter"""
        self._state = RateLimiterState()
        logger.info("rate_limiter_reset", provider=self.provider)


# Rate limiters globais por provider
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(provider: str) -> RateLimiter:
    """Obtem rate limiter singleton para um provider"""
    if provider not in _limiters:
        _limiters[provider] = RateLimiter(provider=provider)
    return _limiters[provider]


async def rate_limited_request(provider: str, func, *args, **kwargs):
    """
    Executa funcao com rate limiting

    Args:
        provider: Nome do provider
        func: Funcao a executar
        *args, **kwargs: Argumentos da funcao

    Returns:
        Resultado da funcao
    """
    limiter = get_rate_limiter(provider)
    await limiter.wait()
    return await func(*args, **kwargs)
