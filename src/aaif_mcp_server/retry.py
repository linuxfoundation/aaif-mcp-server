"""Retry utilities for connector resilience."""

import asyncio
import functools
import logging
from typing import Callable, Type

logger = logging.getLogger(__name__)

class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exception types to retry on
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} retries exhausted for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator


class CircuitBreaker:
    """Simple circuit breaker for connector health management.

    States: closed (normal) → open (failing) → half-open (testing)
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = "closed"
        self._last_failure_time: float = 0

    @property
    def state(self) -> str:
        if self._state == "open":
            import time
            if (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._state = "half_open"
        return self._state

    def record_success(self):
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def check(self):
        if self.state == "open":
            raise CircuitOpenError(
                f"Circuit breaker is open after {self._failure_count} failures. "
                f"Recovery in {self.recovery_timeout}s"
            )
