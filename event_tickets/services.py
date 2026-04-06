from django.utils import timezone
from django.db import transaction
from event_tickets.models import Booking, Payment


def process_payment(booking, method, transaction_id=''):
    with transaction.atomic():
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            method=method,
            transaction_id=transaction_id,
            status=Payment.Status.COMPLETED,
            paid_at=timezone.now(),
        )
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=['status', 'updated_at'])
        return payment
