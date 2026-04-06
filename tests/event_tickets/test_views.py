import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from event_tickets.models import EventCategory, Event, TicketType, Booking, Payment

User = get_user_model()


@pytest.mark.django_db
class TestEventAPI:
    def test_organizer_can_create_event(self, organizer_client, organizer_user):
        cat = EventCategory.objects.create(name='Conference', slug='conference')
        url = reverse('event-list')
        data = {
            'title': 'Dev Conference',
            'slug': 'dev-conference',
            'description': 'Annual dev conference',
            'category': cat.id,
            'venue': 'Convention Center',
            'start_date': (timezone.now() + timezone.timedelta(days=60)).isoformat(),
            'end_date': (timezone.now() + timezone.timedelta(days=61)).isoformat(),
            'capacity': 300,
        }
        response = organizer_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['organizer'] == organizer_user.id

    def test_list_published_events(self, authenticated_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        Event.objects.create(
            title='Published Event',
            slug='published-event',
            description='Desc',
            category=cat,
            organizer=organizer_user,
            venue='Venue',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=4),
            capacity=100,
            is_published=True,
        )
        Event.objects.create(
            title='Draft Event',
            slug='draft-event',
            description='Desc',
            category=cat,
            organizer=organizer_user,
            venue='Venue',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=30, hours=4),
            capacity=100,
            is_published=False,
        )
        url = reverse('event-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_organizer_sees_all_own_events(self, organizer_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        Event.objects.create(title='Published', slug='pub', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100, is_published=True)
        Event.objects.create(title='Draft', slug='draft', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100, is_published=False)
        url = reverse('event-list')
        response = organizer_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_retrieve_event(self, authenticated_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='My Event', slug='my-event', description='Desc', category=cat, organizer=organizer_user, venue='Venue', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100, is_published=True)
        url = reverse('event-detail', kwargs={'slug': 'my-event'})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'My Event'

    def test_publish_event(self, organizer_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Unpublished', slug='unpublished', description='Desc', category=cat, organizer=organizer_user, venue='Venue', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100, is_published=False)
        url = reverse('event-publish', kwargs={'slug': 'unpublished'})
        response = organizer_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        event.refresh_from_db()
        assert event.is_published is True

    def test_customer_cannot_publish(self, authenticated_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Test', slug='test-cust', description='Desc', category=cat, organizer=organizer_user, venue='Venue', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100, is_published=False)
        url = reverse('event-publish', kwargs={'slug': 'test-cust'})
        response = authenticated_client.post(url)
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_upcoming_events(self, authenticated_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        Event.objects.create(title='Future', slug='future', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100, is_published=True)
        Event.objects.create(title='Past', slug='past', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() - timezone.timedelta(days=10), end_date=timezone.now() - timezone.timedelta(days=9), capacity=100, is_published=True)
        url = reverse('event-upcoming')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_event_stats(self, organizer_client, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        Event.objects.create(title='Event', slug='stats-event', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100, is_published=True)
        url = reverse('event-stats')
        response = organizer_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_events' in response.data


@pytest.mark.django_db
class TestBookingAPI:
    def test_create_booking(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-evt', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        url = reverse('booking-list')
        response = authenticated_client.post(url, {'ticket_type_id': tt.id, 'quantity': 2}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['booking_code'].startswith('EVT-')
        assert response.data['total_price'] == '100.00'

    def test_booking_reduces_availability(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-avail', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=10, quantity_available=10, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        url = reverse('booking-list')
        authenticated_client.post(url, {'ticket_type_id': tt.id, 'quantity': 3}, format='json')
        tt.refresh_from_db()
        assert tt.quantity_available == 7

    def test_cannot_book_more_than_available(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-limit', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=5, quantity_available=2, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        url = reverse('booking-list')
        response = authenticated_client.post(url, {'ticket_type_id': tt.id, 'quantity': 5}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_book_expired_sale(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-expired', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=30), sale_end=timezone.now() - timezone.timedelta(days=1))
        url = reverse('booking-list')
        response = authenticated_client.post(url, {'ticket_type_id': tt.id, 'quantity': 1}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_booking(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-cancel', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        booking = Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=2, total_price=100.00, booking_code='EVT-CANCEL', status=Booking.Status.PENDING)
        url = reverse('booking-cancel', kwargs={'pk': booking.id})
        response = authenticated_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED
        tt.refresh_from_db()
        assert tt.quantity_available == 102

    def test_my_bookings(self, authenticated_client, customer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        other_user = User.objects.create_user(email='other@test.com', password='pass')
        event = Event.objects.create(title='Concert', slug='concert-my', description='D', category=cat, organizer=other_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=1, total_price=50.00, booking_code='EVT-MINE', status=Booking.Status.CONFIRMED)
        url = reverse('booking-my-bookings')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_customer_cannot_see_others_bookings(self, authenticated_client, agent_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-other', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        Booking.objects.create(user=agent_user, event=event, ticket_type=tt, quantity=1, total_price=50.00, booking_code='EVT-OTHER', status=Booking.Status.CONFIRMED)
        url = reverse('booking-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


@pytest.mark.django_db
class TestPaymentAPI:
    def test_create_payment(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-pay', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        booking = Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=1, total_price=50.00, booking_code='EVT-PAY', status=Booking.Status.PENDING)
        url = f'/api/events/bookings/{booking.id}/payments/create/'
        response = authenticated_client.post(url, {'method': 'credit_card'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'completed'
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED

    def test_cannot_pay_cancelled_booking(self, authenticated_client, customer_user, organizer_user):
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Concert', slug='concert-cancel-pay', description='D', category=cat, organizer=organizer_user, venue='Arena', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=30, hours=4), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        booking = Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=1, total_price=50.00, booking_code='EVT-CANCELLED', status=Booking.Status.CANCELLED)
        url = f'/api/events/bookings/{booking.id}/payments/create/'
        response = authenticated_client.post(url, {'method': 'credit_card'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
