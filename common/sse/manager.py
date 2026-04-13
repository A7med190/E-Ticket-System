import json
import logging
from typing import AsyncIterator, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class SSEClient:
    def __init__(self, group_name: str, client_id: str):
        self.group_name = group_name
        self.client_id = client_id

    async def send_event(self, event_type: str, data: dict):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                self.group_name,
                {
                    'type': 'sse_message',
                    'event': event_type,
                    'data': data,
                }
            )

    async def receive(self) -> AsyncIterator[dict]:
        from channels.generic.websocket import AsyncJsonWebsocketConsumer
        yield


class SSEManager:
    def __init__(self):
        self.settings = getattr(settings, 'SSE_SETTINGS', {})
        self.heartbeat_interval = self.settings.get('HEARTBEAT_INTERVAL', 30)
        self.retry_time = self.settings.get('RETRY_TIME', 5000)

    def get_channel_name(self, group: str) -> str:
        return f'sse_{group}'

    async def broadcast_to_group(self, group: str, event_type: str, data: dict):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                self.get_channel_name(group),
                {
                    'type': 'sse_message',
                    'event': event_type,
                    'data': data,
                    'retry': self.retry_time,
                }
            )

    async def broadcast_booking_update(self, booking_id: int, status: str):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                'bookings',
                {
                    'type': 'sse_message',
                    'event': 'booking.updated',
                    'data': {
                        'booking_id': booking_id,
                        'status': status,
                    },
                    'retry': self.retry_time,
                }
            )

    async def broadcast_ticket_status(self, ticket_id: int, status: str):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                'tickets',
                {
                    'type': 'sse_message',
                    'event': 'ticket.status_changed',
                    'data': {
                        'ticket_id': ticket_id,
                        'status': status,
                    },
                    'retry': self.retry_time,
                }
            )

    async def broadcast_notification(self, user_id: int, notification: dict):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                f'user_{user_id}',
                {
                    'type': 'sse_message',
                    'event': 'notification',
                    'data': notification,
                    'retry': self.retry_time,
                }
            )


sse_manager = SSEManager()


def format_sse_event(event_type: str, data: dict, retry: int = None) -> str:
    formatted = f'event: {event_type}\ndata: {json.dumps(data)}\n'
    if retry:
        formatted += f'retry: {retry}\n'
    formatted += '\n'
    return formatted


def parse_sse_accept_header(accept_header: str) -> list[str]:
    if not accept_header:
        return ['text/event-stream']
    return [m.strip() for m in accept_header.split(',')]
