import logging
from typing import Optional, List
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, user=None):
        self.user = user
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

    def send_email(self, to: str, subject: str, template: str, context: dict = None) -> bool:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        try:
            context = context or {}
            html_message = render_to_string(template, context)
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f'Email sent to {to}: {subject}')
            return True
        except Exception as e:
            logger.error(f'Failed to send email to {to}: {e}')
            return False

    def send_booking_confirmation(self, booking) -> bool:
        return self.send_email(
            to=booking.user.email,
            subject=f'Booking Confirmation - {booking.booking_code}',
            template='emails/booking_confirmation.html',
            context={
                'booking': booking,
                'event': booking.event,
                'user': booking.user,
            },
        )

    def send_ticket_status_update(self, booking, old_status: str, new_status: str) -> bool:
        subject = f'Your Ticket Status Has Been Updated - {booking.booking_code}'
        return self.send_email(
            to=booking.user.email,
            subject=subject,
            template='emails/ticket_status_update.html',
            context={
                'booking': booking,
                'old_status': old_status,
                'new_status': new_status,
            },
        )

    def send_support_ticket_confirmation(self, ticket) -> bool:
        return self.send_email(
            to=ticket.reporter.email,
            subject=f'Support Ticket Received - {ticket.ticket_number}',
            template='emails/ticket_confirmation.html',
            context={
                'ticket': ticket,
            },
        )

    def send_ticket_assignment_notification(self, ticket, assignee) -> bool:
        return self.send_email(
            to=assignee.email,
            subject=f'New Support Ticket Assigned - {ticket.ticket_number}',
            template='emails/ticket_assigned.html',
            context={
                'ticket': ticket,
                'assignee': assignee,
            },
        )

    def send_ticket_status_notification(self, ticket) -> bool:
        return self.send_email(
            to=ticket.reporter.email,
            subject=f'Support Ticket Status Update - {ticket.ticket_number}',
            template='emails/ticket_status_notification.html',
            context={
                'ticket': ticket,
            },
        )

    def send_event_reminder(self, booking) -> bool:
        from django.utils import timezone
        event = booking.event
        hours_until = (event.start_date - timezone.now()).total_seconds() / 3600
        if hours_until > 48 or hours_until < 0:
            return False
        return self.send_email(
            to=booking.user.email,
            subject=f'Reminder: {event.title} is coming up!',
            template='emails/event_reminder.html',
            context={
                'booking': booking,
                'event': event,
            },
        )

    def create_in_app_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = 'info',
        related_object_type: str = None,
        related_object_id: int = None,
    ) -> dict:
        from notifications.models import Notification
        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )
        from common.sse.manager import sse_manager
        from asgiref.sync import async_to_sync
        async_to_sync(sse_manager.broadcast_notification)(
            user_id,
            {
                'id': notification.id,
                'title': title,
                'message': message,
                'type': notification_type,
            }
        )
        return notification

    def notify_booking_update(self, booking, old_status: str, new_status: str):
        self.send_ticket_status_update(booking, old_status, new_status)
        self.create_in_app_notification(
            user_id=booking.user_id,
            title=f'Booking {booking.booking_code} Updated',
            message=f'Your booking status has been updated from {old_status} to {new_status}.',
            notification_type='booking',
            related_object_type='booking',
            related_object_id=booking.id,
        )

    def notify_ticket_created(self, ticket):
        self.send_support_ticket_confirmation(ticket)
        self.create_in_app_notification(
            user_id=ticket.reporter_id,
            title=f'Ticket {ticket.ticket_number} Created',
            message=f'Your support ticket has been created and is awaiting assignment.',
            notification_type='ticket',
            related_object_type='ticket',
            related_object_id=ticket.id,
        )

    def notify_ticket_assigned(self, ticket):
        if ticket.assignee:
            self.send_ticket_assignment_notification(ticket, ticket.assignee)
            self.create_in_app_notification(
                user_id=ticket.assignee_id,
                title=f'New Ticket Assigned - {ticket.ticket_number}',
                message=f'A new support ticket has been assigned to you.',
                notification_type='ticket',
                related_object_type='ticket',
                related_object_id=ticket.id,
            )

    def notify_ticket_status_changed(self, ticket):
        self.send_ticket_status_notification(ticket)
        self.create_in_app_notification(
            user_id=ticket.reporter_id,
            title=f'Ticket {ticket.ticket_number} Status Update',
            message=f'Your support ticket status has been updated to {ticket.status}.',
            notification_type='ticket',
            related_object_type='ticket',
            related_object_id=ticket.id,
        )


notification_service = NotificationService()
