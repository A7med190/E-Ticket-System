from django.db.models.signals import post_save
from django.dispatch import receiver
from support_tickets.models import SupportTicket


@receiver(post_save, sender=SupportTicket)
def on_ticket_status_change(sender, instance, created, **kwargs):
    pass
