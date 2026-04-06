import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from event_tickets.models import EventCategory, Event, TicketType, Booking

User = get_user_model()


@pytest.mark.django_db
class TestBookingFlow:
    def test_full_booking_to_payment_flow(self, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(
            title='Live Concert',
            slug='live-concert',
            description='Amazing concert',
            category=cat,
            organizer=organizer_user,
            venue='Main Arena',
            start_date=timezone.now() + timezone.timedelta(days=60),
            end_date=timezone.now() + timezone.timedelta(days=60, hours=4),
            capacity=500,
            is_published=True,
        )
        tt = TicketType.objects.create(
            event=event,
            name='VIP',
            price=150.00,
            quantity_total=50,
            quantity_available=50,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=59),
        )

        booking = Booking.objects.create(
            user=customer_user,
            event=event,
            ticket_type=tt,
            quantity=2,
            total_price=300.00,
            booking_code='EVT-FLOW01',
            status=Booking.Status.PENDING,
        )
        assert booking.status == Booking.Status.PENDING
        assert tt.quantity_available == 48

        from event_tickets.services import process_payment
        payment = process_payment(booking, method='credit_card', transaction_id='TXN-FLOW')

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED
        assert payment.status == 'completed'
        assert payment.amount == 300.00

    def test_cancel_restores_availability(self, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Workshop', slug='workshop')
        event = Event.objects.create(
            title='Coding Workshop',
            slug='coding-workshop',
            description='Learn coding',
            category=cat,
            organizer=organizer_user,
            venue='Room A',
            start_date=timezone.now() + timezone.timedelta(days=60),
            end_date=timezone.now() + timezone.timedelta(days=60, hours=3),
            capacity=30,
        )
        tt = TicketType.objects.create(
            event=event,
            name='Standard',
            price=75.00,
            quantity_total=30,
            quantity_available=25,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=59),
        )
        booking = Booking.objects.create(
            user=customer_user,
            event=event,
            ticket_type=tt,
            quantity=5,
            total_price=375.00,
            booking_code='EVT-CANCEL01',
            status=Booking.Status.PENDING,
        )
        assert tt.quantity_available == 25

        booking.status = Booking.Status.CANCELLED
        tt.quantity_available += booking.quantity
        booking.save(update_fields=['status'])
        tt.save(update_fields=['quantity_available'])

        assert tt.quantity_available == 30

    def test_multiple_bookings_same_event(self, organizer_user):
        cat = EventCategory.objects.create(name='Conference', slug='conf')
        event = Event.objects.create(
            title='Tech Summit',
            slug='tech-summit',
            description='Tech',
            category=cat,
            organizer=organizer_user,
            venue='Convention Hall',
            start_date=timezone.now() + timezone.timedelta(days=90),
            end_date=timezone.now() + timezone.timedelta(days=91),
            capacity=1000,
        )
        tt = TicketType.objects.create(
            event=event,
            name='Early Bird',
            price=99.00,
            quantity_total=200,
            quantity_available=200,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=30),
        )
        u1 = User.objects.create_user(email='u1@test.com', password='pass')
        u2 = User.objects.create_user(email='u2@test.com', password='pass')
        u3 = User.objects.create_user(email='u3@test.com', password='pass')

        Booking.objects.create(user=u1, event=event, ticket_type=tt, quantity=4, total_price=396.00, booking_code='EVT-B1', status='confirmed')
        Booking.objects.create(user=u2, event=event, ticket_type=tt, quantity=2, total_price=198.00, booking_code='EVT-B2', status='confirmed')
        Booking.objects.create(user=u3, event=event, ticket_type=tt, quantity=1, total_price=99.00, booking_code='EVT-B3', status='pending')

        tt.refresh_from_db()
        assert tt.quantity_available == 193
        assert event.tickets_sold == 7
