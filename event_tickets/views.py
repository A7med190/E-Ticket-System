from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from common.permissions import IsAdmin, IsOrganizerOrAdmin, IsEventOrganizerOrAdmin, IsBookingOwnerOrAdmin
from common.filters import EventFilter, BookingFilter
from common.utils import export_to_csv, generate_qr_code
from event_tickets.models import EventCategory, Event, TicketType, Booking, Payment
from event_tickets.serializers import (
    EventCategorySerializer, EventSerializer, EventListSerializer, EventCreateSerializer,
    TicketTypeSerializer, BookingSerializer, BookingListSerializer, BookingCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer,
)
from event_tickets.services import process_payment
from notifications.services import create_notification
from notifications.tasks import send_booking_confirmation_email_task


class EventCategoryViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = (IsAuthenticated,)
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'created_at')
    ordering = ('name',)


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = EventFilter
    search_fields = ('title', 'description', 'venue', 'venue_address')
    ordering_fields = ('start_date', 'end_date', 'created_at', 'title')
    ordering = ('-start_date',)
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        qs = Event.objects.select_related('category', 'organizer').prefetch_related('ticket_types')
        if user.role == 'admin':
            return qs
        if user.role == 'organizer':
            return qs.filter(Q(organizer=user) | Q(is_published=True))
        return qs.filter(is_published=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        if self.action == 'create':
            return EventCreateSerializer
        return EventSerializer

    def perform_create(self, serializer):
        event = serializer.save()
        create_notification(
            user=event.organizer,
            notification_type='ticket_created',
            title='Event Created',
            message=f'Your event "{event.title}" has been created.',
            related_object_id=str(event.id),
        )

    @action(detail=True, methods=['post'], permission_classes=[IsOrganizerOrAdmin])
    def publish(self, request, slug=None):
        event = self.get_object()
        if event.organizer != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        event.is_published = True
        event.save(update_fields=['is_published', 'updated_at'])
        create_notification(
            user=event.organizer,
            notification_type='ticket_status_changed',
            title='Event Published',
            message=f'Your event "{event.title}" is now published.',
            related_object_id=str(event.id),
        )
        return Response({'message': 'Event published.'})

    @action(detail=False, methods=['get'], permission_classes=[IsOrganizerOrAdmin])
    def stats(self, request):
        qs = self.get_queryset()
        total_events = qs.count()
        total_bookings = Booking.objects.filter(event__in=qs).count()
        total_revenue = Booking.objects.filter(event__in=qs, status=Booking.Status.CONFIRMED).aggregate(
            total=Sum('total_price')
        )['total'] or 0
        upcoming = qs.filter(start_date__gte=timezone.now(), is_published=True).count()

        return Response({
            'total_events': total_events,
            'total_bookings': total_bookings,
            'total_revenue': str(total_revenue),
            'upcoming_events': upcoming,
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        qs = self.get_queryset().filter(start_date__gte=timezone.now(), is_published=True)
        serializer = EventListSerializer(qs[:20], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='ticket-types')
    def ticket_types(self, request, slug=None):
        event = self.get_object()
        if request.method == 'GET':
            types = event.ticket_types.all()
            serializer = TicketTypeSerializer(types, many=True)
            return Response(serializer.data)
        if request.user.role not in ('organizer', 'admin') or event.organizer != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TicketTypeSerializer(data={**request.data, 'event': event.id}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = BookingFilter
    search_fields = ('booking_code',)
    ordering_fields = ('created_at', 'total_price')
    ordering = ('-created_at',)

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related('event', 'ticket_type', 'user').prefetch_related('payments')
        if user.role == 'admin':
            return qs
        if user.role == 'organizer':
            return qs.filter(event__organizer=user)
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        create_notification(
            user=booking.user,
            notification_type='booking_confirmed',
            title='Booking Created',
            message=f'Booking {booking.booking_code} for {booking.event.title} has been created.',
            related_object_id=str(booking.id),
        )
        send_booking_confirmation_email_task.delay(booking.id)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in (Booking.Status.CANCELLED, Booking.Status.REFUNDED):
            return Response({'error': 'Booking is already cancelled or refunded.'}, status=status.HTTP_400_BAD_REQUEST)
        if booking.event.start_date < timezone.now():
            return Response({'error': 'Cannot cancel booking for a past event.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = Booking.Status.CANCELLED
        booking.ticket_type.quantity_available += booking.quantity
        booking.ticket_type.save(update_fields=['quantity_available'])
        booking.save(update_fields=['status', 'updated_at'])

        create_notification(
            user=booking.user,
            notification_type='booking_cancelled',
            title='Booking Cancelled',
            message=f'Booking {booking.booking_code} has been cancelled.',
            related_object_id=str(booking.id),
        )
        return Response({'message': 'Booking cancelled.'})

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        qs = Booking.objects.filter(user=request.user).select_related('event', 'ticket_type')
        serializer = BookingListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def export(self, request):
        qs = self.get_queryset()
        field_names = ('booking_code', 'user', 'event', 'ticket_type', 'quantity', 'total_price', 'status', 'created_at')
        return export_to_csv(qs, field_names, 'bookings')


class PaymentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        booking_id = self.kwargs.get('booking_pk')
        return Payment.objects.filter(booking_id=booking_id)

    @action(detail=False, methods=['post'], url_path='create')
    def create_payment(self, request, booking_pk=None):
        try:
            booking = Booking.objects.get(id=booking_pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role != 'admin' and booking.user != request.user and booking.event.organizer != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PaymentCreateSerializer(data=request.data, context={'booking': booking, 'request': request})
        serializer.is_valid(raise_exception=True)

        payment = process_payment(
            booking=booking,
            method=serializer.validated_data['method'],
            transaction_id=serializer.validated_data.get('transaction_id', ''),
        )

        create_notification(
            user=booking.user,
            notification_type='payment_completed',
            title='Payment Completed',
            message=f'Payment for booking {booking.booking_code} has been completed.',
            related_object_id=str(booking.id),
        )

        if booking.status == Booking.Status.CONFIRMED and not booking.qr_code:
            generate_qr_code(booking)
            booking.save(update_fields=['qr_code'])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
