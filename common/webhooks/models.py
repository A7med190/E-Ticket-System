import requests
import logging
import hashlib
import hmac
import time
from typing import Any, Callable, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class WebhookDeliveryStatus:
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'


class WebhookDelivery(models.Model):
    webhook_url = models.ForeignKey('WebhookEndpoint', on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=[
        (WebhookDeliveryStatus.SUCCESS, 'Success'),
        (WebhookDeliveryStatus.FAILED, 'Failed'),
        (WebhookDeliveryStatus.PENDING, 'Pending'),
    ], default=WebhookDeliveryStatus.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    response_status_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webhook_deliveries'
        ordering = ('-created_at',)


class WebhookEndpoint(models.Model):
    url = models.URLField(max_length=500)
    event_types = models.JSONField(default=list)
    secret = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webhook_endpoints'

    def __str__(self):
        return self.url


class WebhookService:
    def __init__(self):
        self.settings = getattr(settings, 'WEBHOOK_SETTINGS', {})
        self.max_retries = self.settings.get('MAX_RETRIES', 3)
        self.retry_delay = self.settings.get('RETRY_DELAY', 60)
        self.timeout = self.settings.get('TIMEOUT', 30)
        self.secret_key = self.settings.get('SECRET_KEY', '')

    def generate_signature(self, payload: str, timestamp: str) -> str:
        message = f'{timestamp}.{payload}'
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f'sha256={signature}'

    def prepare_headers(self, payload: dict) -> dict:
        import json
        payload_str = json.dumps(payload, separators=(',', ':'))
        timestamp = str(int(time.time()))
        signature = self.generate_signature(payload_str, timestamp)
        return {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Timestamp': timestamp,
            'User-Agent': 'E-Ticket-Webhook/1.0',
        }

    def send_webhook(self, url: str, payload: dict, headers: dict = None) -> tuple[bool, dict]:
        delivery_headers = self.prepare_headers(payload)
        if headers:
            delivery_headers.update(headers)

        try:
            response = requests.post(
                url,
                json=payload,
                headers=delivery_headers,
                timeout=self.timeout,
            )
            success = 200 <= response.status_code < 300
            return success, {
                'status_code': response.status_code,
                'response': response.text[:1000] if response.text else '',
            }
        except requests.Timeout:
            return False, {'error': 'Request timeout'}
        except requests.RequestException as e:
            return False, {'error': str(e)}

    def send_to_endpoints(self, event_type: str, payload: dict) -> list[WebhookDelivery]:
        from .models import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus
        endpoints = WebhookEndpoint.objects.filter(
            is_active=True,
            event_types__contains=[event_type],
        )
        deliveries = []
        for endpoint in endpoints:
            delivery = WebhookDelivery.objects.create(
                webhook_url=endpoint,
                event_type=event_type,
                payload=payload,
            )
            success, result = self.send_webhook(endpoint.url, payload)
            delivery.attempt_count = 1
            if success:
                delivery.status = WebhookDeliveryStatus.SUCCESS
                delivery.delivered_at = timezone.now()
            else:
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.error_message = result.get('error', '')
            delivery.response_status_code = result.get('status_code')
            delivery.response_body = result.get('response', '')
            delivery.save()
            deliveries.append(delivery)
        return deliveries

    def retry_failed_delivery(self, delivery: WebhookDelivery) -> bool:
        from .models import WebhookDeliveryStatus
        if delivery.attempt_count >= self.max_retries:
            return False
        success, result = self.send_webhook(
            delivery.webhook_url.url,
            delivery.payload,
        )
        delivery.attempt_count += 1
        if success:
            delivery.status = WebhookDeliveryStatus.SUCCESS
            delivery.delivered_at = timezone.now()
            delivery.error_message = ''
        else:
            delivery.error_message = result.get('error', '')
            if delivery.attempt_count >= self.max_retries:
                delivery.status = WebhookDeliveryStatus.FAILED
        delivery.response_status_code = result.get('status_code')
        delivery.response_body = result.get('response', '')
        delivery.save()
        return success


webhook_service = WebhookService()


def dispatch_webhook(event_type: str, payload: dict):
    from .models import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus
    from celery import shared_task
    shared_task(webhook_service.send_to_endpoints)(event_type, payload)


from django.db import models
from django.utils import timezone
