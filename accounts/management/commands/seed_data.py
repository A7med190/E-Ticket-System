from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import User
from event_tickets.models import Event, TicketType
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding E-Ticket System database...')

        # Create admin
        if not User.objects.filter(email='admin@eticket.com').exists():
            User.objects.create_superuser(
                email='admin@eticket.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )

        # Create test users
        for i in range(5):
            email = f'user{i+1}@example.com'
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=fake.first_name(),
                    last_name=fake.last_name()
                )

        # Create events
        events_data = [
            ('Tech Conference 2024', 'Annual technology conference'),
            ('Music Festival', 'Live music event'),
            ('Comedy Night', 'Stand-up comedy show'),
            ('Art Exhibition', 'Modern art showcase'),
            ('Sports Match', 'Championship game'),
        ]

        for name, desc in events_data:
            event_date = datetime.now() + timedelta(days=random.randint(7, 60))
            event, created = Event.objects.get_or_create(
                title=name,
                defaults={
                    'description': desc,
                    'date': event_date,
                    'venue': fake.city(),
                    'total_capacity': random.randint(100, 1000),
                    'status': 'published'
                }
            )
            if created:
                # Create ticket types
                for ticket_type in ['General', 'VIP', 'Early Bird']:
                    TicketType.objects.create(
                        event=event,
                        name=ticket_type,
                        price=round(random.uniform(20, 200), 2),
                        quantity=random.randint(50, 500)
                    )

        self.stdout.write(self.style.SUCCESS('Successfully seeded E-Ticket database!'))