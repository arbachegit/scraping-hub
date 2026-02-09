"""
Circuit Breaker Pattern Implementation.

Protege contra falhas em cascata quando serviços externos estão instáveis.

Estados:
- CLOSED: Normal, requisições passam
- OPEN: Muitas falhas, requisições falham imediatamente (fail fast)
- HALF_OPEN: Testando se o serviço voltou

Uso:
    breaker = CircuitBreaker(name="serper", failure_threshold=5)

    if breaker.can_execute():
        try:
            result = await api_call()
            breaker.record_success()
        except Exception as e:
            breaker.record_failure()
            raise
    else:
        raise CircuitOpenError("Service unavailable")
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Estados do Circuit Breaker."""
    CLOSED = "closed"      # Normal - requisições passam
    OPEN = "open"          # Falhas demais - requisições bloqueadas
    HALF_OPEN = "half_open"  # Testando recuperação


class CircuitOpenError(Exception):
    """Exceção lançada quando o circuito está aberto."""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. "
            f"Retry after {retry_after:.1f} seconds."
        )


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker para proteger contra falhas em cascata.

    Args:
        name: Nome identificador do circuito (ex: "serper", "tavily")
        failure_threshold: Número de falhas para abrir o circuito
        success_threshold: Sucessos necessários em HALF_OPEN para fechar
        timeout: Segundos para tentar novamente após OPEN
    """
    name: str
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0

    # Estado interno
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _success_count: int = field(default=0, repr=False)
    _last_failure_time: Optional[float] = field(default=None, repr=False)

    @property
    def state(self) -> CircuitState:
        """Retorna estado atual, verificando timeout."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_closed(self) -> bool:
        """Verifica se está fechado (normal)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Verifica se está aberto (bloqueando)."""
        return self.state == CircuitState.OPEN

    def can_execute(self) -> bool:
        """
        Verifica se pode executar uma requisição.

        Returns:
            True se pode executar, False se circuito aberto
        """
        state = self.state
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Registra uma execução bem-sucedida."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Registra uma falha."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Qualquer falha em HALF_OPEN reabre o circuito
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def get_retry_after(self) -> float:
        """Retorna segundos restantes até poder tentar novamente."""
        if self._last_failure_time is None:
            return 0.0

        elapsed = time.time() - self._last_failure_time
        remaining = self.timeout - elapsed
        return max(0.0, remaining)

    def reset(self) -> None:
        """Reset manual do circuito."""
        self._transition_to(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info("circuit_breaker_reset", name=self.name)

    def get_stats(self) -> Dict:
        """Retorna estatísticas do circuito."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
            "retry_after": self.get_retry_after() if self.is_open else 0
        }

    def _should_attempt_reset(self) -> bool:
        """Verifica se deve tentar resetar (timeout expirado)."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transiciona para novo estado."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0

        logger.info(
            "circuit_breaker_transition",
            name=self.name,
            from_state=old_state.value,
            to_state=new_state.value
        )


class CircuitBreakerRegistry:
    """
    Registry global de Circuit Breakers.

    Permite gerenciar múltiplos circuitos por nome.
    """
    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_or_create(
        cls,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0
    ) -> CircuitBreaker:
        """
        Obtém ou cria um Circuit Breaker.

        Args:
            name: Nome único do circuito
            failure_threshold: Falhas para abrir
            success_threshold: Sucessos para fechar
            timeout: Segundos até tentar novamente

        Returns:
            CircuitBreaker existente ou novo
        """
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout
            )
        return cls._breakers[name]

    @classmethod
    def get(cls, name: str) -> Optional[CircuitBreaker]:
        """Obtém um Circuit Breaker por nome."""
        return cls._breakers.get(name)

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict]:
        """Retorna estatísticas de todos os circuitos."""
        return {
            name: breaker.get_stats()
            for name, breaker in cls._breakers.items()
        }

    @classmethod
    def reset_all(cls) -> None:
        """Reset de todos os circuitos."""
        for breaker in cls._breakers.values():
            breaker.reset()


# Alias para uso direto
get_circuit_breaker = CircuitBreakerRegistry.get_or_create
