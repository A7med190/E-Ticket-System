import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from event_tickets.models import EventCategory, Event, TicketType, Booking, Payment

User = get_user_model()


@pytest.mark.django_db
class TestEventModel:
    def test_create_event(self, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(
            title='Summer Festival',
            slug='summer-festival',
            description='A great festival',
            category=cat,
            organizer=organizer_user,
            venue='Central Park',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=6),
            capacity=500,
        )
        assert event.title == 'Summer Festival'
        assert event.is_published is False
        assert event.capacity == 500
        assert str(event) == 'Summer Festival'

    def test_create_ticket_type(self, organizer_user):
        cat = EventCategory.objects.create(name='Conference', slug='conference')
        event = Event.objects.create(
            title='Tech Conf',
            slug='tech-conf',
            description='Tech conference',
            category=cat,
            organizer=organizer_user,
            venue='Convention Center',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=31),
            capacity=200,
        )
        tt = TicketType.objects.create(
            event=event,
            name='VIP',
            price=150.00,
            quantity_total=50,
            quantity_available=50,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=29),
        )
        assert tt.price == 150.00
        assert tt.is_on_sale is True
        assert str(tt) == 'VIP - Tech Conf'

    def test_ticket_type_not_on_sale(self, organizer_user):
        cat = EventCategory.objects.create(name='Sports', slug='sports')
        event = Event.objects.create(
            title='Match',
            slug='match',
            description='A match',
            category=cat,
            organizer=organizer_user,
            venue='Stadium',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=3),
            capacity=1000,
        )
        tt = TicketType.objects.create(
            event=event,
            name='General',
            price=25.00,
            quantity_total=100,
            quantity_available=100,
            sale_start=timezone.now() + timezone.timedelta(days=10),
            sale_end=timezone.now() + timezone.timedelta(days=20),
        )
        assert tt.is_on_sale is False

    def test_create_booking(self, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(
            title='Rock Concert',
            slug='rock-concert',
            description='Rock concert',
            category=cat,
            organizer=organizer_user,
            venue='Arena',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=4),
            capacity=100,
        )
        tt = TicketType.objects.create(
            event=event,
            name='General',
            price=50.00,
            quantity_total=100,
            quantity_available=100,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=29),
        )
        booking = Booking.objects.create(
            user=customer_user,
            event=event,
            ticket_type=tt,
            quantity=2,
            total_price=100.00,
            booking_code='EVT-ABC123',
        )
        assert booking.quantity == 2
        assert booking.total_price == 100.00
        assert booking.status == Booking.Status.PENDING
        assert str(booking) == 'EVT-ABC123 - Rock Concert'

    def test_create_payment(self, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(
            title='Jazz Night',
            slug='jazz-night',
            description='Jazz',
            category=cat,
            organizer=organizer_user,
            venue='Club',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=3),
            capacity=50,
        )
        tt = TicketType.objects.create(
            event=event,
            name='VIP',
            price=200.00,
            quantity_total=10,
            quantity_available=10,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=29),
        )
        booking = Booking.objects.create(
            user=customer_user,
            event=event,
            ticket_type=tt,
            quantity=1,
            total_price=200.00,
            booking_code='EVT-XYZ789',
        )
        payment = Payment.objects.create(
            booking=booking,
            amount=200.00,
            method=Payment.Method.CREDIT_CARD,
            status=Payment.Status.COMPLETED,
            transaction_id='TXN-001',
            paid_at=timezone.now(),
        )
        assert payment.amount == 200.00
        assert payment.method == Payment.Method.CREDIT_CARD
        assert str(payment) == 'credit_card - EVT-XYZ789 - completed'

    def test_event_tickets_sold(self, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(
            title='Festival',
            slug='festival',
            description='Festival',
            category=cat,
            organizer=organizer_user,
            venue='Park',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=8),
            capacity=100,
        )
        tt = TicketType.objects.create(
            event=event,
            name='General',
            price=30.00,
            quantity_total=100,
            quantity_available=95,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=29),
        )
        Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=3, total_price=90.00, booking_code='EVT-001', status='confirmed')
        Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=2, total_price=60.00, booking_code='EVT-002', status='confirmed')
        assert event.tickets_sold == 5

    def test_event_is_sold_out(self, organizer_user):
        cat = EventCategory.objects.create(name='Workshop', slug='workshop')
        event = Event.objects.create(
            title='Small Workshop',
            slug='small-workshop',
            description='WS',
            category=cat,
            organizer=organizer_user,
            venue='Room 1',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=2),
            capacity=2,
        )
        tt = TicketType.objects.create(
            event=event,
            name='Standard',
            price=10.00,
            quantity_total=2,
            quantity_available=0,
            sale_start=timezone.now() - timezone.timedelta(days=1),
            sale_end=timezone.now() + timezone.timedelta(days=29),
        )
        assert event.is_sold_out is False
        assert tt.quantity_available == 0
