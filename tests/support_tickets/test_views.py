import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from support_tickets.models import SupportCategory, SupportTicket, TicketComment

User = get_user_model()


@pytest.mark.django_db
class TestSupportCategoryAPI:
    def test_list_categories(self, authenticated_client):
        SupportCategory.objects.create(name='Technical', slug='technical')
        SupportCategory.objects.create(name='Billing', slug='billing')
        url = reverse('support-category-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_retrieve_category(self, authenticated_client):
        cat = SupportCategory.objects.create(name='Technical', slug='technical', description='Tech support')
        url = reverse('support-category-detail', kwargs={'pk': cat.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Technical'


@pytest.mark.django_db
class TestSupportTicketAPI:
    def test_customer_can_create_ticket(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        url = reverse('support-ticket-list')
        data = {'title': 'Login Issue', 'description': 'Cannot login', 'priority': 'high', 'category': cat.id}
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['ticket_number'].startswith('SUP-')
        assert SupportTicket.objects.filter(reporter=customer_user).exists()

    def test_customer_sees_own_tickets(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='My Ticket', description='Desc', category=cat, reporter=customer_user)
        url = reverse('support-ticket-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_customer_cannot_see_others_tickets(self, authenticated_client, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='Other Ticket', description='Desc', category=cat, reporter=agent_user)
        url = reverse('support-ticket-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_retrieve_ticket(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='My Ticket', description='Desc', category=cat, reporter=customer_user)
        url = reverse('support-ticket-detail', kwargs={'pk': ticket.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'My Ticket'

    def test_agent_can_see_assigned_tickets(self, agent_client, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='Assigned', description='Desc', category=cat, reporter=customer_user, assignee=agent_user)
        url = reverse('support-ticket-list')
        response = agent_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_agent_can_change_status(self, agent_client, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user, assignee=agent_user)
        url = reverse('support-ticket-change-status', kwargs={'pk': ticket.id})
        response = agent_client.post(url, {'status': 'in_progress'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.status == 'in_progress'

    def test_agent_can_assign(self, agent_client, customer_user, agent_user, admin_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        url = reverse('support-ticket-assign', kwargs={'pk': ticket.id})
        response = agent_client.post(url, {'agent_id': agent_user.id}, format='json')
        assert response.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.assignee == agent_user

    def test_customer_cannot_change_status(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        url = reverse('support-ticket-change-status', kwargs={'pk': ticket.id})
        response = authenticated_client.post(url, {'status': 'resolved'}, format='json')
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_add_comment(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        url = f'/api/support/tickets/{ticket.id}/comments/'
        response = authenticated_client.post(url, {'body': 'Here is more info'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert TicketComment.objects.filter(ticket=ticket).count() == 1

    def test_list_comments(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user)
        TicketComment.objects.create(ticket=ticket, author=customer_user, body='Comment 1')
        url = f'/api/support/tickets/{ticket.id}/comments/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_customer_cannot_see_internal_comments(self, authenticated_client, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Test', description='Desc', category=cat, reporter=customer_user, assignee=agent_user)
        TicketComment.objects.create(ticket=ticket, author=agent_user, body='Internal note', is_internal=True)
        TicketComment.objects.create(ticket=ticket, author=agent_user, body='Public reply', is_internal=False)
        url = f'/api/support/tickets/{ticket.id}/comments/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_stats_endpoint(self, agent_client, customer_user, agent_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='T1', description='D1', category=cat, reporter=customer_user, assignee=agent_user, status='open')
        SupportTicket.objects.create(title='T2', description='D2', category=cat, reporter=customer_user, assignee=agent_user, status='in_progress')
        url = reverse('support-ticket-stats')
        response = agent_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 2
        assert response.data['open_count'] == 1

    def test_filter_by_status(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='Open', description='D1', category=cat, reporter=customer_user, status='open')
        SupportTicket.objects.create(title='Resolved', description='D2', category=cat, reporter=customer_user, status='resolved')
        url = reverse('support-ticket-list')
        response = authenticated_client.get(url, {'status': 'open'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_search_tickets(self, authenticated_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        SupportTicket.objects.create(title='Login Problem', description='Cannot access', category=cat, reporter=customer_user)
        SupportTicket.objects.create(title='Billing Issue', description='Wrong charge', category=cat, reporter=customer_user)
        url = reverse('support-ticket-list')
        response = authenticated_client.get(url, {'search': 'Login'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_delete_ticket_as_admin(self, admin_client, customer_user):
        cat = SupportCategory.objects.create(name='General', slug='general')
        ticket = SupportTicket.objects.create(title='Delete Me', description='Desc', category=cat, reporter=customer_user)
        url = reverse('support-ticket-detail', kwargs={'pk': ticket.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SupportTicket.objects.filter(id=ticket.id).exists()
