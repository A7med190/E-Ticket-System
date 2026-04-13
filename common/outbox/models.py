import json
import logging
from datetime import datetime
from typing import Any, Optional
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class OutboxStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class OutboxMessage(models.Model):
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING
    )
    destination = models.URLField(max_length=500)
    headers = models.JSONField(default=dict, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'outbox_messages'
        ordering = ('created_at',)
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.event_type} - {self.status}'


class OutboxManager:
    def create_message(
        self,
        event_type: str,
        destination: str,
        payload: dict,
        headers: Optional[dict] = None,
        max_retries: int = 3,
    ) -> OutboxMessage:
        return OutboxMessage.objects.create(
            event_type=event_type,
            destination=destination,
            payload=payload,
            headers=headers or {},
            max_retries=max_retries,
            next_retry_at=timezone.now(),
        )

    def get_pending_messages(self, batch_size: int = 100):
        return OutboxMessage.objects.filter(
            status=OutboxStatus.PENDING,
            next_retry_at__lte=timezone.now(),
        ).order_by('created_at')[:batch_size]

    def mark_processing(self, message: OutboxMessage):
        message.status = OutboxStatus.PROCESSING
        message.save(update_fields=['status'])

    def mark_sent(self, message: OutboxMessage):
        message.status = OutboxStatus.SENT
        message.processed_at = timezone.now()
        message.save(update_fields=['status', 'processed_at'])

    def mark_failed(self, message: OutboxMessage, error: str):
        message.retry_count += 1
        if message.retry_count >= message.max_retries:
            message.status = OutboxStatus.FAILED
        else:
            message.status = OutboxStatus.PENDING
            from datetime import timedelta
            message.next_retry_at = timezone.now() + timedelta(minutes=message.retry_count * 5)
        message.error_message = error
        message.save()


outbox_manager = OutboxManager()


def publish_event(
    event_type: str,
    destination: str,
    payload: dict,
    headers: Optional[dict] = None,
    max_retries: int = 3,
) -> OutboxMessage:
    return outbox_manager.create_message(
        event_type=event_type,
        destination=destination,
        payload=payload,
        headers=headers,
        max_retries=max_retries,
    )


def publish_booking_created(booking, destination: str):
    return publish_event(
        event_type='booking.created',
        destination=destination,
        payload={
            'booking_id': booking.id,
            'booking_code': booking.booking_code,
            'user_id': booking.user_id,
            'event_id': booking.event_id,
            'quantity': booking.quantity,
            'total_price': str(booking.total_price),
            'status': booking.status,
            'created_at': booking.created_at.isoformat() if booking.created_at else None,
        },
    )


def publish_ticket_status_changed(booking, old_status: str, new_status: str, destination: str):
    return publish_event(
        event_type='booking.status_changed',
        destination=destination,
        payload={
            'booking_id': booking.id,
            'booking_code': booking.booking_code,
            'old_status': old_status,
            'new_status': new_status,
            'changed_at': timezone.now().isoformat(),
        },
    )


def publish_support_ticket_created(ticket, destination: str):
    return publish_event(
        event_type='ticket.created',
        destination=destination,
        payload={
            'ticket_id': ticket.id,
            'ticket_number': ticket.ticket_number,
            'subject': ticket.subject,
            'reporter_id': ticket.reporter_id,
            'status': ticket.status,
            'priority': ticket.priority,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        },
    )


def publish_support_ticket_assigned(ticket, assignee_id: int, destination: str):
    return publish_event(
        event_type='ticket.assigned',
        destination=destination,
        payload={
            'ticket_id': ticket.id,
            'ticket_number': ticket.ticket_number,
            'assignee_id': assignee_id,
            'assigned_at': timezone.now().isoformat(),
        },
    )
