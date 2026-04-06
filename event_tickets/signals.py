from django.db.models.signals import post_save
from django.dispatch import receiver
from event_tickets.models import Booking


@receiver(post_save, sender=Booking)
def on_booking_created(sender, instance, created, **kwargs):
    pass
