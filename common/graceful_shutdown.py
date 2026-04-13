import os
import signal
import sys
import logging
import threading
from typing import Callable, Optional
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    def __init__(self, shutdown_timeout: int = 30):
        self.shutdown_timeout = shutdown_timeout
        self.shutting_down = threading.Event()
        self._shutdown_hooks: list[Callable] = []
        self._registered = False

    def register_hooks(self, *hooks: Callable):
        for hook in hooks:
            self.add_shutdown_hook(hook)

    def add_shutdown_hook(self, hook: Callable):
        if hook not in self._shutdown_hooks:
            self._shutdown_hooks.append(hook)

    def remove_shutdown_hook(self, hook: Callable):
        if hook in self._shutdown_hooks:
            self._shutdown_hooks.remove(hook)

    def execute_hooks(self):
        logger.info(f'Executing {len(self._shutdown_hooks)} shutdown hooks...')
        for hook in reversed(self._shutdown_hooks):
            try:
                logger.info(f'Executing shutdown hook: {hook.__name__}')
                hook()
            except Exception as e:
                logger.error(f'Error in shutdown hook {hook.__name__}: {e}')

    def shutdown(self, signum=None, frame=None):
        if self.shutting_down.is_set():
            return
        self.shutting_down.set()
        logger.info('Graceful shutdown initiated...')
        self.execute_hooks()
        logger.info('Graceful shutdown completed')

    def register_signals(self):
        if self._registered:
            return
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, self.shutdown)
            signal.signal(signal.SIGINT, self.shutdown)
        self._registered = True

    def is_shutting_down(self) -> bool:
        return self.shutting_down.is_set()


def shutdown_celery_workers():
    from django_celery_results.models import TaskResult
    logger.info('Marking pending tasks...')


def close_database_connections():
    from django.db import connection
    connection.close()
    logger.info('Database connections closed')


def flush_outbox():
    from common.outbox.tasks import process_outbox_messages
    try:
        process_outbox_messages()
    except Exception as e:
        logger.error(f'Error flushing outbox during shutdown: {e}')


def cleanup_sessions():
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    Session.objects.filter(expire_date__lt=timezone.now()).delete()
    logger.info('Expired sessions cleaned up')


shutdown_handler = GracefulShutdownHandler(
    shutdown_timeout=getattr(settings, 'GRACEFUL_SHUTDOWN', {}).get('SHUTDOWN_TIMEOUT', 30)
)


def setup_graceful_shutdown():
    shutdown_handler.register_hooks(
        flush_outbox,
        shutdown_celery_workers,
        cleanup_sessions,
        close_database_connections,
    )
    shutdown_handler.register_signals()
    logger.info('Graceful shutdown handlers registered')


class ShutdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if shutdown_handler.is_shutting_down():
            from django.http import HttpResponseServerError
            return HttpResponseServerError('Service is shutting down')
        response = self.get_response(request)
        return response
