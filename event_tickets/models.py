from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator


class EventCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'event_categories'
        verbose_name_plural = 'Event Categories'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    category = models.ForeignKey(EventCategory, on_delete=models.PROTECT, related_name='events')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    venue = models.CharField(max_length=255)
    venue_address = models.TextField(blank=True, default='')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        ordering = ('-start_date',)
        indexes = [
            models.Index(fields=['is_published', 'start_date']),
            models.Index(fields=['organizer']),
        ]

    def __str__(self):
        return self.title

    @property
    def tickets_sold(self):
        from django.db.models import Sum
        result = self.bookings.filter(status__in=['pending', 'confirmed']).aggregate(total=models.Sum('quantity'))
        return result['total'] or 0

    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.capacity


class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity_total = models.PositiveIntegerField()
    quantity_available = models.PositiveIntegerField()
    sale_start = models.DateTimeField()
    sale_end = models.DateTimeField()
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'ticket_types'
        ordering = ('price',)

    def __str__(self):
        return f'{self.name} - {self.event.title}'

    @property
    def is_on_sale(self):
        from django.utils import timezone
        now = timezone.now()
        return self.sale_start <= now <= self.sale_end and self.quantity_available > 0


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    booking_code = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='bookings')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    qr_code = models.ImageField(upload_to='tickets/qr/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['event']),
            models.Index(fields=['booking_code']),
        ]

    def __str__(self):
        return f'{self.booking_code} - {self.event.title}'


class Payment(models.Model):
    class Method(models.TextChoices):
        CREDIT_CARD = 'credit_card', _('Credit Card')
        DEBIT_CARD = 'debit_card', _('Debit Card')
        PAYPAL = 'paypal', _('PayPal')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        CASH = 'cash', _('Cash')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.method} - {self.booking.booking_code} - {self.status}'
