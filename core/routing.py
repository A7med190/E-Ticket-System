import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from common.consumers import (
    SSEGroupConsumer,
    UserNotificationConsumer,
    BookingUpdatesConsumer,
    TicketUpdatesConsumer,
)

websocket_urlpatterns = [
    path('ws/sse/<str:group>/', SSEGroupConsumer.as_asgi()),
    path('ws/notifications/', UserNotificationConsumer.as_asgi()),
    path('ws/bookings/', BookingUpdatesConsumer.as_asgi()),
    path('ws/tickets/', TicketUpdatesConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
