import hashlib
import json
import logging
from django.http import HttpRequest, HttpResponse
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.settings = getattr(settings, 'IDEMPOTENCY_SETTINGS', {})
        self.header_name = self.settings.get('HEADER_NAME', 'X-Idempotency-Key')
        self.cache_timeout = self.settings.get('CACHE_TIMEOUT', 86400)
        self.stored_status_codes = self.settings.get('STORED_STATUS_CODES', [200, 201, 204])
        self.cache_alias = 'idempotency'

    def get_cache_key(self, key: str) -> str:
        return f'idempotency:{key}'

    def process_request(self, request: HttpRequest) -> None:
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None

        idempotency_key = request.headers.get(self.header_name)
        if not idempotency_key:
            return None

        cache_key = self.get_cache_key(idempotency_key)
        cached_response = cache.get(cache_key, using=self.cache_alias)

        if cached_response:
            logger.info(f'Idempotency key reused: {idempotency_key}')
            response_data = json.loads(cached_response)
            return HttpResponse(
                content=response_data['body'],
                status=response_data['status'],
                content_type=response_data.get('content_type', 'application/json'),
            )

        request.idempotency_key = idempotency_key
        request._idempotency_cache_key = cache_key
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if not getattr(request, '_idempotency_cache_key', None):
            return response

        if response.status_code not in self.stored_status_codes:
            return response

        cache_key = request._idempotency_cache_key
        response_data = {
            'body': response.content.decode('utf-8'),
            'status': response.status_code,
            'content_type': response.get('Content-Type', 'application/json'),
        }
        cache.set(cache_key, json.dumps(response_data), timeout=self.cache_timeout, using=self.cache_alias)
        response[self.header_name] = request.idempotency_key
        return response


class IdempotencyService:
    def __init__(self):
        self.settings = getattr(settings, 'IDEMPOTENCY_SETTINGS', {})
        self.cache_timeout = self.settings.get('CACHE_TIMEOUT', 86400)
        self.cache_alias = 'idempotency'

    def get_cache_key(self, key: str) -> str:
        return f'idempotency:{key}'

    def generate_key_from_request(self, request_data: dict, endpoint: str) -> str:
        content = json.dumps({'endpoint': endpoint, 'data': request_data}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def check_exists(self, key: str) -> bool:
        cache_key = self.get_cache_key(key)
        return cache.get(cache_key, using=self.cache_alias) is not None

    def get_cached_response(self, key: str) -> dict:
        cache_key = self.get_cache_key(key)
        cached = cache.get(cache_key, using=self.cache_alias)
        if cached:
            return json.loads(cached)
        return None

    def store_response(self, key: str, response_data: dict) -> None:
        cache_key = self.get_cache_key(key)
        cache.set(cache_key, json.dumps(response_data), timeout=self.cache_timeout, using=self.cache_alias)

    def delete_key(self, key: str) -> None:
        cache_key = self.get_cache_key(key)
        cache.delete(cache_key, using=self.cache_alias)
