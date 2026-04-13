import time
import functools
import logging
from enum import Enum
from typing import Any, Callable, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class CircuitBreakerError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = '',
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or 'default'
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._failure_count = 0
        return self._state

    def _update_cache(self):
        cache_key = f'circuit_breaker_{self.name}'
        cache.set(cache_key, {
            'state': self._state.value,
            'failure_count': self._failure_count,
            'last_failure_time': self._last_failure_time,
        }, timeout=self.recovery_timeout * 2)

    def _load_cache(self):
        cache_key = f'circuit_breaker_{self.name}'
        data = cache.get(cache_key)
        if data:
            self._state = CircuitState(data['state'])
            self._failure_count = data['failure_count']
            self._last_failure_time = data['last_failure_time']

    def record_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._update_cache()

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
        self._update_cache()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f'Circuit breaker {self.name} is OPEN')
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise

    def __enter__(self):
        self._load_cache()
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f'Circuit breaker {self.name} is OPEN')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.expected_exception):
            self.record_failure()
        elif self.state != CircuitState.OPEN:
            self.record_success()
        return False


def circuit_breaker(
    failure_threshold: int = None,
    recovery_timeout: int = None,
    expected_exception: type = Exception,
    name: str = '',
):
    settings_config = getattr(settings, 'CIRCUIT_BREAKER_SETTINGS', {})
    threshold = failure_threshold or settings_config.get('FAILURE_THRESHOLD', 5)
    timeout = recovery_timeout or settings_config.get('RECOVERY_TIMEOUT', 60)
    
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f'{func.__module__}.{func.__name__}'
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            breaker = CircuitBreaker(
                failure_threshold=threshold,
                recovery_timeout=timeout,
                expected_exception=expected_exception,
                name=breaker_name,
            )
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


class CircuitBreakerMixin:
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    circuit_breaker_expected_exception: type = Exception

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        if not hasattr(self, '_circuit_breaker'):
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=self.circuit_breaker_failure_threshold,
                recovery_timeout=self.circuit_breaker_recovery_timeout,
                expected_exception=self.circuit_breaker_expected_exception,
                name=f'{self.__class__.__module__}.{self.__class__.__name__}',
            )
        return self._circuit_breaker

    def circuit_protected_call(self, func: Callable, *args, **kwargs) -> Any:
        return self.circuit_breaker.call(func, *args, **kwargs)
