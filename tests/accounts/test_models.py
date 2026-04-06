import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        assert user.email == 'test@example.com'
        assert user.role == User.Role.CUSTOMER
        assert user.is_email_verified is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password('testpass123')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == User.Role.ADMIN

    def test_user_str(self):
        user = User.objects.create_user(email='test@example.com', password='pass', first_name='', last_name='')
        assert str(user) == 'test@example.com'

    def test_role_properties(self):
        admin = User.objects.create_user(email='admin@test.com', password='pass', role=User.Role.ADMIN)
        agent = User.objects.create_user(email='agent@test.com', password='pass', role=User.Role.AGENT)
        organizer = User.objects.create_user(email='org@test.com', password='pass', role=User.Role.ORGANIZER)
        customer = User.objects.create_user(email='cust@test.com', password='pass', role=User.Role.CUSTOMER)

        assert admin.is_admin is True
        assert agent.is_agent is True
        assert organizer.is_organizer is True
        assert customer.is_customer is True

    def test_email_unique(self):
        User.objects.create_user(email='unique@test.com', password='pass')
        with pytest.raises(Exception):
            User.objects.create_user(email='unique@test.com', password='pass2')
