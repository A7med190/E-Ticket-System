from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

User = get_user_model()


def send_html_email(to_email, subject, template_name, context):
    context['frontend_url'] = settings.FRONTEND_URL
    html_content = render_to_string(f'emails/{template_name}.html', context)
    from_email = settings.DEFAULT_FROM_EMAIL
    email = EmailMultiAlternatives(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=[to_email],
    )
    email.attach_alternative(html_content, 'text/html')
    email.send()


@shared_task
def send_verification_email_task(user_id, uidb64, token):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    send_html_email(
        to_email=user.email,
        subject='Verify your email - E-Ticketing System',
        template_name='email_verification',
        context={
            'user': user,
            'uidb64': uidb64,
            'token': token,
            'verify_url': f'{settings.FRONTEND_URL}/verify-email/{uidb64}/{token}/',
        },
    )


@shared_task
def send_password_reset_email_task(user_id, uidb64, token):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    send_html_email(
        to_email=user.email,
        subject='Password Reset - E-Ticketing System',
        template_name='password_reset',
        context={
            'user': user,
            'uidb64': uidb64,
            'token': token,
            'reset_url': f'{settings.FRONTEND_URL}/reset-password/{uidb64}/{token}/',
        },
    )


@shared_task
def send_ticket_created_email_task(ticket_id):
    from support_tickets.models import SupportTicket
    try:
        ticket = SupportTicket.objects.select_related('reporter').get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return
    send_html_email(
        to_email=ticket.reporter.email,
        subject=f'Ticket {ticket.ticket_number} Created',
        template_name='ticket_created',
        context={'user': ticket.reporter, 'ticket': ticket},
    )


@shared_task
def send_ticket_assigned_email_task(ticket_id, agent_id):
    from support_tickets.models import SupportTicket
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        agent = User.objects.get(id=agent_id)
    except Exception:
        return
    send_html_email(
        to_email=agent.email,
        subject=f'Ticket {ticket.ticket_number} Assigned to You',
        template_name='ticket_assigned',
        context={'user': agent, 'ticket': ticket},
    )


@shared_task
def send_ticket_status_changed_email_task(ticket_id):
    from support_tickets.models import SupportTicket
    try:
        ticket = SupportTicket.objects.select_related('reporter').get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return
    send_html_email(
        to_email=ticket.reporter.email,
        subject=f'Ticket {ticket.ticket_number} Status Updated',
        template_name='ticket_status_changed',
        context={'user': ticket.reporter, 'ticket': ticket},
    )


@shared_task
def send_booking_confirmation_email_task(booking_id):
    from event_tickets.models import Booking
    try:
        booking = Booking.objects.select_related('user', 'event', 'ticket_type').get(id=booking_id)
    except Booking.DoesNotExist:
        return
    send_html_email(
        to_email=booking.user.email,
        subject=f'Booking Confirmation - {booking.booking_code}',
        template_name='booking_confirmed',
        context={'user': booking.user, 'booking': booking},
    )


@shared_task
def send_booking_cancelled_email_task(booking_id):
    from event_tickets.models import Booking
    try:
        booking = Booking.objects.select_related('user', 'event').get(id=booking_id)
    except Booking.DoesNotExist:
        return
    send_html_email(
        to_email=booking.user.email,
        subject=f'Booking Cancelled - {booking.booking_code}',
        template_name='booking_cancelled',
        context={'user': booking.user, 'booking': booking},
    )


@shared_task
def send_event_reminders():
    from event_tickets.models import Event
    now = timezone.now()
    upcoming = Event.objects.filter(
        is_published=True,
        start_date__gt=now,
        start_date__lte=now + timezone.timedelta(hours=24),
    )
    for event in upcoming:
        for booking in event.bookings.filter(status=Booking.Status.CONFIRMED).select_related('user'):
            send_html_email(
                to_email=booking.user.email,
                subject=f'Reminder: {event.title} starts soon!',
                template_name='event_reminder',
                context={'user': booking.user, 'event': event, 'booking': booking},
            )


@shared_task
def cleanup_expired_bookings():
    from event_tickets.models import Booking
    expired = Booking.objects.filter(
        status=Booking.Status.PENDING,
        created_at__lt=timezone.now() - timezone.timedelta(minutes=30),
    )
    for booking in expired:
        booking.status = Booking.Status.CANCELLED
        booking.ticket_type.quantity_available += booking.quantity
        booking.ticket_type.save(update_fields=['quantity_available'])
        booking.save(update_fields=['status', 'updated_at'])
