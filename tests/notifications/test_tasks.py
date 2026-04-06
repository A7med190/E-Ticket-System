import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import Notification

User = get_user_model()


@pytest.mark.django_db
class TestNotificationModel:
    def test_create_notification(self, customer_user):
        n = Notification.objects.create(
            user=customer_user,
            type=Notification.Type.TICKET_CREATED,
            title='Ticket Created',
            message='Your ticket has been created.',
        )
        assert n.is_read is False
        assert n.user == customer_user
        assert str(n) == f'Ticket Created - {customer_user.email}'

    def test_mark_as_read(self, customer_user):
        n = Notification.objects.create(
            user=customer_user,
            type=Notification.Type.TICKET_CREATED,
            title='Test',
            message='Test message',
        )
        n.is_read = True
        n.save()
        assert n.is_read is True

    def test_notification_ordering(self, customer_user):
        n1 = Notification.objects.create(user=customer_user, type=Notification.Type.TICKET_CREATED, title='First', message='M1')
        n2 = Notification.objects.create(user=customer_user, type=Notification.Type.BOOKING_CONFIRMED, title='Second', message='M2')
        notifications = list(Notification.objects.filter(user=customer_user))
        assert notifications[0] == n2
        assert notifications[1] == n1


@pytest.mark.django_db
class TestNotificationTasks:
    def test_send_verification_email_task(self, customer_user):
        from notifications.tasks import send_verification_email_task
        result = send_verification_email_task.apply(args=[customer_user.id, 'uid', 'token'])
        assert result.successful()

    def test_send_password_reset_email_task(self, customer_user):
        from notifications.tasks import send_password_reset_email_task
        result = send_password_reset_email_task.apply(args=[customer_user.id, 'uid', 'token'])
        assert result.successful()

    def test_send_booking_confirmation_email_task(self, customer_user, organizer_user):
        from event_tickets.models import EventCategory, Event, TicketType, Booking
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Test', slug='test-email', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=100, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        booking = Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=1, total_price=50.00, booking_code='EVT-EMAIL', status='confirmed')

        from notifications.tasks import send_booking_confirmation_email_task
        result = send_booking_confirmation_email_task.apply(args=[booking.id])
        assert result.successful()

    def test_cleanup_expired_bookings(self, customer_user, organizer_user):
        from event_tickets.models import EventCategory, Event, TicketType, Booking
        from django.utils import timezone
        cat = EventCategory.objects.create(name='Concert', slug='concert')
        event = Event.objects.create(title='Test', slug='test-cleanup', description='D', category=cat, organizer=organizer_user, venue='V', start_date=timezone.now() + timezone.timedelta(days=30), end_date=timezone.now() + timezone.timedelta(days=31), capacity=100)
        tt = TicketType.objects.create(event=event, name='General', price=50.00, quantity_total=100, quantity_available=95, sale_start=timezone.now() - timezone.timedelta(days=1), sale_end=timezone.now() + timezone.timedelta(days=29))
        Booking.objects.create(user=customer_user, event=event, ticket_type=tt, quantity=5, total_price=250.00, booking_code='EVT-OLD', status='pending', created_at=timezone.now() - timezone.timedelta(hours=1))

        from notifications.tasks import cleanup_expired_bookings
        cleanup_expired_bookings.apply()

        booking = Booking.objects.get(booking_code='EVT-OLD')
        assert booking.status == 'cancelled'
        tt.refresh_from_db()
        assert tt.quantity_available == 100
