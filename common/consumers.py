import json
import logging
from typing import Optional
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class SSEGroupConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = self.scope['url_route']['kwargs'].get('group', 'global')
        self.room_group_name = f'sse_{self.group_name}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f'WebSocket connected to group: {self.group_name}')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f'WebSocket disconnected from group: {self.group_name}')

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get('type', 'ping')
            
            if event_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp'),
                }))
            elif event_type == 'subscribe':
                new_group = data.get('group', self.group_name)
                if new_group != self.group_name:
                    await self.channel_layer.group_discard(
                        self.room_group_name,
                        self.channel_name
                    )
                    self.group_name = new_group
                    self.room_group_name = f'sse_{new_group}'
                    await self.channel_layer.group_add(
                        self.room_group_name,
                        self.channel_name
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'subscribed',
                        'group': new_group,
                    }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))

    async def sse_message(self, event):
        await self.send(text_data=json.dumps({
            'event': event.get('event', 'message'),
            'data': event.get('data', {}),
            'retry': event.get('retry', 5000),
        }))


class UserNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope.get('user') or not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        self.user_id = self.scope['user'].id
        self.room_group_name = f'user_{self.user_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f'User {self.user_id} connected to notifications')

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        logger.info(f'User notifications disconnected')

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event.get('data', {}),
        }))

    async def sse_message(self, event):
        await self.send(text_data=json.dumps({
            'event': event.get('event', 'message'),
            'data': event.get('data', {}),
        }))


class BookingUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'bookings'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info('Client connected to booking updates')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def booking_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'booking_update',
            'data': event.get('data', {}),
        }))

    async def sse_message(self, event):
        await self.send(text_data=json.dumps({
            'event': event.get('event', 'message'),
            'data': event.get('data', {}),
        }))


class TicketUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'tickets'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info('Client connected to ticket updates')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def ticket_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ticket_update',
            'data': event.get('data', {}),
        }))

    async def sse_message(self, event):
        await self.send(text_data=json.dumps({
            'event': event.get('event', 'message'),
            'data': event.get('data', {}),
        }))
