import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email='admin@eticket.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role=User.Role.ADMIN,
        is_email_verified=True,
    )


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        email='agent@eticket.com',
        password='agentpass123',
        first_name='Agent',
        last_name='User',
        role=User.Role.AGENT,
        is_email_verified=True,
    )


@pytest.fixture
def organizer_user(db):
    return User.objects.create_user(
        email='organizer@eticket.com',
        password='orgpass123',
        first_name='Organizer',
        last_name='User',
        role=User.Role.ORGANIZER,
        is_email_verified=True,
    )


@pytest.fixture
def customer_user(db):
    return User.objects.create_user(
        email='customer@eticket.com',
        password='custpass123',
        first_name='Customer',
        last_name='User',
        role=User.Role.CUSTOMER,
        is_email_verified=True,
    )


@pytest.fixture
def unverified_user(db):
    return User.objects.create_user(
        email='unverified@eticket.com',
        password='unverified123',
        first_name='Unverified',
        last_name='User',
        role=User.Role.CUSTOMER,
        is_email_verified=False,
    )


@pytest.fixture
def authenticated_client(api_client, customer_user):
    api_client.force_authenticate(user=customer_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def agent_client(api_client, agent_user):
    api_client.force_authenticate(user=agent_user)
    return api_client


@pytest.fixture
def organizer_client(api_client, organizer_user):
    api_client.force_authenticate(user=organizer_user)
    return api_client
