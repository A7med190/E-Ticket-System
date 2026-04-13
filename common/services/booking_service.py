import logging
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, user=None):
        self.user = user

    def create_booking(
        self,
        event_id: int,
        ticket_type_id: int,
        quantity: int,
        user_id: int = None,
    ) -> dict:
        from event_tickets.models import Event, TicketType, Booking
        from accounts.models import User
        user = user or User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)
        ticket_type = TicketType.objects.get(id=ticket_type_id, event=event)

        if not ticket_type.is_on_sale:
            raise ValidationError('Ticket sales are not currently available for this ticket type')
        if ticket_type.quantity_available < quantity:
            raise ValidationError('Not enough tickets available')

        total_price = ticket_type.price * quantity
        import uuid
        booking_code = f'BK{uuid.uuid4().hex[:8].upper()}'

        with transaction.atomic():
            ticket_type.quantity_available -= quantity
            ticket_type.save(update_fields=['quantity_available'])

            booking = Booking.objects.create(
                booking_code=booking_code,
                user=user,
                event=event,
                ticket_type=ticket_type,
                quantity=quantity,
                total_price=total_price,
                status=Booking.Status.PENDING,
            )

        from common.sse.manager import sse_manager
        from asgiref.sync import async_to_sync
        async_to_sync(sse_manager.broadcast_booking_update)(booking.id, booking.status)

        return {
            'booking': booking,
            'total_price': total_price,
        }

    def confirm_booking(self, booking_id: int, payment_method: str = 'credit_card') -> dict:
        from event_tickets.models import Booking, Payment
        from django.utils import timezone

        booking = Booking.objects.get(id=booking_id)
        if booking.status != Booking.Status.PENDING:
            raise ValidationError('Booking is not in pending status')

        with transaction.atomic():
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                method=payment_method,
                status=Payment.Status.PENDING,
            )

            payment.status = Payment.Status.COMPLETED
            payment.paid_at = timezone.now()
            payment.save()

            old_status = booking.status
            booking.status = Booking.Status.CONFIRMED
            booking.save()

        from common.sse.manager import sse_manager
        from asgiref.sync import async_to_sync
        async_to_sync(sse_manager.broadcast_booking_update)(booking.id, booking.status)

        return {
            'booking': booking,
            'payment': payment,
        }

    def cancel_booking(self, booking_id: int, reason: str = None) -> dict:
        from event_tickets.models import Booking, TicketType
        from django.utils import timezone

        booking = Booking.objects.get(id=booking_id)
        if booking.status == Booking.Status.CANCELLED:
            raise ValidationError('Booking is already cancelled')
        if booking.status == Booking.Status.REFUNDED:
            raise ValidationError('Booking has already been refunded')

        with transaction.atomic():
            ticket_type = booking.ticket_type
            ticket_type.quantity_available += booking.quantity
            ticket_type.save(update_fields=['quantity_available'])

            old_status = booking.status
            booking.status = Booking.Status.CANCELLED
            booking.save()

        from common.sse.manager import sse_manager
        from asgiref.sync import async_to_sync
        async_to_sync(sse_manager.broadcast_booking_update)(booking.id, booking.status)

        return {
            'booking': booking,
            'tickets_returned': booking.quantity,
        }

    def refund_booking(self, booking_id: int) -> dict:
        from event_tickets.models import Booking, Payment
        from common.circuit_breaker import circuit_breaker, CircuitBreakerError

        booking = Booking.objects.get(id=booking_id)
        if booking.status == Booking.Status.REFUNDED:
            raise ValidationError('Booking has already been refunded')

        payment = booking.payments.filter(status=Payment.Status.COMPLETED).first()
        if not payment:
            raise ValidationError('No completed payment found for this booking')

        try:
            with circuit_breaker(f'payment_refund_{payment.id}', failure_threshold=3):
                pass
        except CircuitBreakerError:
            raise ValidationError('Payment processor is currently unavailable. Please try again later.')

        with transaction.atomic():
            payment.status = Payment.Status.REFUNDED
            payment.save()

            booking.status = Booking.Status.REFUNDED
            booking.save()

        from common.sse.manager import sse_manager
        from asgiref.sync import async_to_sync
        async_to_sync(sse_manager.broadcast_booking_update)(booking.id, booking.status)

        return {
            'booking': booking,
            'refund_payment': payment,
        }
