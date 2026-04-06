from django.apps import AppConfig


class EventTicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'event_tickets'

    def ready(self):
        import event_tickets.signals
