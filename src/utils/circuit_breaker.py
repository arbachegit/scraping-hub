"""
Circuit Breaker Pattern Implementation

Protects against cascading failures by temporarily disabling
calls to failing services.
"""

import time
from enum import Enum
from threading import Lock
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""

    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit open for {service_name}. Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service is failing, calls are rejected
    - HALF_OPEN: Testing if service recovered

    Args:
        name: Service name for logging
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        success_threshold: Successes needed in HALF_OPEN to close
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting calls)."""
        return self._state == CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to_half_open()
                    return True
                return False

            # HALF_OPEN: allow limited calls
            return True

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to test recovery."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        logger.info(
            "Circuit half-open, testing recovery",
            service=self.name,
        )

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._close_circuit()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _close_circuit(self) -> None:
        """Close the circuit (normal operation)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit closed, service recovered", service=self.name)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if (
                self._state == CircuitState.HALF_OPEN
                or self._failure_count >= self.failure_threshold
            ):
                self._open_circuit()

    def _open_circuit(self) -> None:
        """Open the circuit (reject calls)."""
        self._state = CircuitState.OPEN
        logger.warning(
            "Circuit opened, service failing",
            service=self.name,
            failure_count=self._failure_count,
        )

    def get_retry_after(self) -> float:
        """Get seconds until retry is allowed."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("api_service")
        if breaker.can_execute():
            try:
                result = call_api()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
                raise
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    success_threshold=success_threshold,
                )
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def reset(self, name: str) -> None:
        """Reset a circuit breaker."""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._lock:
            self._breakers.clear()

    def get_status(self) -> Dict[str, str]:
        """Get status of all circuit breakers."""
        return {name: breaker.state.value for name, breaker in self._breakers.items()}
