import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'cleanup-expired-tickets': {
        'task': 'notifications.tasks.cleanup_expired_tickets',
        'schedule': crontab(hour=2, minute=0),
    },
    'send-event-reminders': {
        'task': 'notifications.tasks.send_event_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
