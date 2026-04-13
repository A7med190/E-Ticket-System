default_app_config = 'common.apps.CommonConfig'

# from .soft_deletes import BaseSoftDeleteModel, IsDeletedManager, AllManager
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerMixin,
    circuit_breaker,
)
from .graceful_shutdown import (
    GracefulShutdownHandler,
    shutdown_handler,
    setup_graceful_shutdown,
)
from .middleware import IdempotencyMiddleware, IdempotencyService

__all__ = [
    'BaseSoftDeleteModel',
    'IsDeletedManager',
    'AllManager',
    'CircuitBreaker',
    'CircuitBreakerError',
    'CircuitBreakerMixin',
    'circuit_breaker',
    'GracefulShutdownHandler',
    'shutdown_handler',
    'setup_graceful_shutdown',
    'IdempotencyMiddleware',
    'IdempotencyService',
]
