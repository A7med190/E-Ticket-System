from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.utils import timezone


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    data = {
        'user': {'email': user.email, 'role': user.role, 'name': user.get_full_name()},
    }

    if user.role == 'admin':
        from support_tickets.models import SupportTicket
        from event_tickets.models import Event, Booking
        data['support'] = {
            'total_tickets': SupportTicket.objects.count(),
            'open': SupportTicket.objects.filter(status='open').count(),
            'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
            'resolved': SupportTicket.objects.filter(status='resolved').count(),
            'closed': SupportTicket.objects.filter(status='closed').count(),
        }
        data['events'] = {
            'total_events': Event.objects.count(),
            'published': Event.objects.filter(is_published=True).count(),
            'upcoming': Event.objects.filter(start_date__gte=timezone.now(), is_published=True).count(),
            'total_bookings': Booking.objects.count(),
            'total_revenue': str(Booking.objects.filter(status='confirmed').aggregate(total=Sum('total_price'))['total'] or 0),
        }
    elif user.role in ('agent',):
        from support_tickets.models import SupportTicket
        data['support'] = {
            'assigned': SupportTicket.objects.filter(assignee=user).count(),
            'open': SupportTicket.objects.filter(assignee=user, status='open').count(),
            'in_progress': SupportTicket.objects.filter(assignee=user, status='in_progress').count(),
            'resolved': SupportTicket.objects.filter(assignee=user, status='resolved').count(),
        }
    elif user.role == 'organizer':
        from event_tickets.models import Event, Booking
        data['events'] = {
            'total_events': Event.objects.filter(organizer=user).count(),
            'published': Event.objects.filter(organizer=user, is_published=True).count(),
            'total_bookings': Booking.objects.filter(event__organizer=user).count(),
            'revenue': str(Booking.objects.filter(event__organizer=user, status='confirmed').aggregate(total=Sum('total_price'))['total'] or 0),
        }
    else:
        from support_tickets.models import SupportTicket
        from event_tickets.models import Booking
        data['support'] = {
            'my_tickets': SupportTicket.objects.filter(reporter=user).count(),
            'open': SupportTicket.objects.filter(reporter=user, status='open').count(),
            'in_progress': SupportTicket.objects.filter(reporter=user, status='in_progress').count(),
        }
        data['bookings'] = {
            'total': Booking.objects.filter(user=user).count(),
            'confirmed': Booking.objects.filter(user=user, status='confirmed').count(),
            'pending': Booking.objects.filter(user=user, status='pending').count(),
        }

    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    from django.db import connection
    from django.core.cache import cache
    from django.utils import timezone
    
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'
    
    try:
        cache.set('health_check', 'ok', 1)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = 'ok'
        else:
            health['checks']['cache'] = 'error: cache not working'
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['cache'] = f'error: {str(e)}'
        health['status'] = 'degraded'
    
    return Response(health, status=200 if health['status'] == 'healthy' else 503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/support/', include('support_tickets.urls')),
    path('api/events/', include('event_tickets.urls')),
    path('api/', include('notifications.urls')),
    path('api/dashboard/', dashboard, name='dashboard'),
    path('api/health/', health_check, name='health_check'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

try:
    from common.sse.views import (
        SSEView,
        UserSSEView,
        GlobalSSEView,
        BookingUpdatesSSEView,
        TicketUpdatesSSEView,
    )
    urlpatterns += [
        path('api/sse/global/', GlobalSSEView.as_view(), name='sse_global'),
        path('api/sse/user/', UserSSEView.as_view(), name='sse_user'),
        path('api/sse/bookings/', BookingUpdatesSSEView.as_view(), name='sse_bookings'),
        path('api/sse/tickets/', TicketUpdatesSSEView.as_view(), name='sse_tickets'),
    ]
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]

admin.site.site_header = 'E-Ticketing System Admin'
admin.site.site_title = 'E-Ticketing Admin'
admin.site.index_title = 'Welcome to E-Ticketing Administration'
