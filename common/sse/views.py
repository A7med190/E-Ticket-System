import asyncio
import json
import logging
from typing import Optional
from django.http import StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class SSEChannelConsumer:
    def __init__(self, channel_layer, group_name: str):
        self.channel_layer = channel_layer
        self.group_name = group_name
        self.queue: asyncio.Queue = asyncio.Queue()

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, 'sse_consumer')

    async def disconnect(self):
        await self.channel_layer.group_discard(self.group_name, 'sse_consumer')

    async def receive(self, message: dict):
        await self.queue.put(message)

    async def event_stream(self):
        while True:
            try:
                message = await asyncio.wait_for(self.queue.get(), timeout=30)
                yield self.format_sse_message(
                    message.get('event', 'message'),
                    message.get('data', {}),
                    message.get('retry')
                )
            except asyncio.TimeoutError:
                yield self.format_sse_message('heartbeat', {'timestamp': None}, 30000)

    def format_sse_message(self, event_type: str, data: dict, retry: Optional[int] = None) -> bytes:
        message = f'event: {event_type}\ndata: {json.dumps(data)}\n'
        if retry:
            message += f'retry: {retry}\n'
        message += '\n'
        return message.encode()


class SSEView(LoginRequiredMixin, View):
    async def get(self, request, group: str = 'global'):
        from django.http import HttpResponseBadRequest
        accept_header = request.headers.get('Accept', '')
        if 'text/event-stream' not in accept_header and accept_header != '*/*':
            return HttpResponseBadRequest('This endpoint requires Accept: text/event-stream header')

        async def event_stream():
            channel_layer = get_channel_layer()
            if not channel_layer:
                yield b'event: error\ndata: {"error": "Channel layer not configured"}\n\n'
                return

            consumer = SSEChannelConsumer(channel_layer, f'sse_{group}')
            await consumer.connect()

            try:
                yield b''
                while True:
                    message = await asyncio.wait_for(consumer.queue.get(), timeout=30)
                    yield consumer.format_sse_message(
                        message.get('event', 'message'),
                        message.get('data', {}),
                        message.get('retry')
                    )
            except asyncio.TimeoutError:
                yield b'event: heartbeat\ndata: {}\n\n'
            except asyncio.CancelledError:
                pass
            finally:
                await consumer.disconnect()

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class UserSSEView(LoginRequiredMixin, View):
    async def get(self, request):
        return await SSEView.as_view().get(request, group=f'user_{request.user.id}')


class GlobalSSEView(LoginRequiredMixin, View):
    async def get(self, request):
        return await SSEView.as_view().get(request, group='global')


class BookingUpdatesSSEView(LoginRequiredMixin, View):
    async def get(self, request):
        return await SSEView.as_view().get(request, group='bookings')


class TicketUpdatesSSEView(LoginRequiredMixin, View):
    async def get(self, request):
        return await SSEView.as_view().get(request, group='tickets')


@sync_to_async
def broadcast_booking_update(booking_id: int, status: str):
    from common.sse.manager import sse_manager
    return sse_manager.broadcast_booking_update(booking_id, status)


@sync_to_async
def broadcast_ticket_status(ticket_id: int, status: str):
    from common.sse.manager import sse_manager
    return sse_manager.broadcast_ticket_status(ticket_id, status)


@sync_to_async
def broadcast_notification(user_id: int, notification: dict):
    from common.sse.manager import sse_manager
    return sse_manager.broadcast_notification(user_id, notification)
