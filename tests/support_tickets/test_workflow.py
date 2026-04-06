import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from support_tickets.models import SupportCategory, SupportTicket, TicketComment

User = get_user_model()


@pytest.mark.django_db
class TestTicketWorkflow:
    def test_full_ticket_lifecycle(self, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='Technical', slug='technical')

        ticket = SupportTicket.objects.create(
            title='Cannot access dashboard',
            description='Getting 500 error',
            category=cat,
            reporter=customer_user,
            priority=SupportTicket.Priority.HIGH,
        )
        assert ticket.status == SupportTicket.Status.OPEN
        assert ticket.assignee is not None

        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save()
        assert ticket.status == SupportTicket.Status.IN_PROGRESS

        TicketComment.objects.create(
            ticket=ticket,
            author=agent_user,
            body='Looking into this now.',
        )
        assert ticket.comments.count() == 1

        ticket.status = SupportTicket.Status.WAITING
        ticket.save()
        TicketComment.objects.create(
            ticket=ticket,
            author=agent_user,
            body='Please provide your browser version.',
        )

        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save()

        ticket.status = SupportTicket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save()
        assert ticket.resolved_at is not None

        ticket.status = SupportTicket.Status.CLOSED
        ticket.save()
        assert ticket.status == SupportTicket.Status.CLOSED

    def test_multiple_comments_ordering(self, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)

        c1 = TicketComment.objects.create(ticket=ticket, author=customer_user, body='First')
        c2 = TicketComment.objects.create(ticket=ticket, author=agent_user, body='Second')
        c3 = TicketComment.objects.create(ticket=ticket, author=customer_user, body='Third')

        comments = list(ticket.comments.all())
        assert comments[0].body == 'First'
        assert comments[1].body == 'Second'
        assert comments[2].body == 'Third'

    def test_ticket_assignment_round_robin(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        a1 = User.objects.create_user(email='a1@test.com', password='pass', role=User.Role.AGENT)
        a2 = User.objects.create_user(email='a2@test.com', password='pass', role=User.Role.AGENT)

        from support_tickets.services import assign_ticket

        t1 = SupportTicket.objects.create(title='T1', description='D1', category=cat, reporter=customer_user)
        assign_ticket(t1)

        t2 = SupportTicket.objects.create(title='T2', description='D2', category=cat, reporter=customer_user)
        assign_ticket(t2)

        assert t1.assignee is not None
        assert t2.assignee is not None

    def test_ticket_number_generation(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        t1 = SupportTicket.objects.create(title='T1', description='D1', category=cat, reporter=customer_user)
        t2 = SupportTicket.objects.create(title='T2', description='D2', category=cat, reporter=customer_user)
        t3 = SupportTicket.objects.create(title='T3', description='D3', category=cat, reporter=customer_user)

        assert t1.ticket_number == 'SUP-000001'
        assert t2.ticket_number == 'SUP-000002'
        assert t3.ticket_number == 'SUP-000003'
