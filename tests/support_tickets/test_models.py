import pytest
from django.contrib.auth import get_user_model
from support_tickets.models import SupportCategory, SupportTicket, TicketComment

User = get_user_model()


@pytest.mark.django_db
class TestSupportTicketModel:
    def test_create_category(self):
        cat = SupportCategory.objects.create(name='Technical', slug='technical', description='Tech issues')
        assert cat.name == 'Technical'
        assert cat.slug == 'technical'
        assert str(cat) == 'Technical'

    def test_create_ticket(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(
            title='Test Issue',
            description='Something is broken',
            category=cat,
            reporter=customer_user,
            priority=SupportTicket.Priority.HIGH,
        )
        assert ticket.status == SupportTicket.Status.OPEN
        assert ticket.priority == SupportTicket.Priority.HIGH
        assert ticket.ticket_number.startswith('SUP-')
        assert str(ticket) == f'{ticket.ticket_number} - Test Issue'

    def test_ticket_number_unique(self, customer_user):
        cat = SupportCategory.objects.create(name='Billing', slug='billing')
        t1 = SupportTicket.objects.create(title='T1', description='D1', category=cat, reporter=customer_user)
        t2 = SupportTicket.objects.create(title='T2', description='D2', category=cat, reporter=customer_user)
        assert t1.ticket_number != t2.ticket_number

    def test_create_comment(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        comment = TicketComment.objects.create(ticket=ticket, author=customer_user, body='This is a comment')
        assert comment.ticket == ticket
        assert comment.author == customer_user
        assert comment.is_internal is False
        assert str(comment) == f'Comment by {customer_user} on {ticket.ticket_number}'

    def test_internal_comment(self, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user, assignee=agent_user)
        comment = TicketComment.objects.create(ticket=ticket, author=agent_user, body='Internal note', is_internal=True)
        assert comment.is_internal is True

    def test_ticket_str(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        assert str(ticket) == f'{ticket.ticket_number} - Test'

    def test_ticket_ordering(self, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        t1 = SupportTicket.objects.create(title='First', description='D1', category=cat, reporter=customer_user)
        t2 = SupportTicket.objects.create(title='Second', description='D2', category=cat, reporter=customer_user)
        tickets = SupportTicket.objects.all()
        assert tickets[0] == t2
        assert tickets[1] == t1
