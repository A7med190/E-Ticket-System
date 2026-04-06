from django.db import models
from django.conf import settings


class Notification(models.Model):
    class Type(models.TextChoices):
        TICKET_CREATED = 'ticket_created', 'Ticket Created'
        TICKET_ASSIGNED = 'ticket_assigned', 'Ticket Assigned'
        TICKET_STATUS_CHANGED = 'ticket_status_changed', 'Ticket Status Changed'
        TICKET_COMMENT = 'ticket_comment', 'New Comment'
        BOOKING_CONFIRMED = 'booking_confirmed', 'Booking Confirmed'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking Cancelled'
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        PAYMENT_COMPLETED = 'payment_completed', 'Payment Completed'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        EMAIL_VERIFICATION = 'email_verification', 'Email Verification'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_object_id = models.CharField(max_length=100, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f'{self.title} - {self.user.email}'
