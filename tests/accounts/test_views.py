import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestAuthEndpoints:
    def test_register(self, api_client):
        url = reverse('register')
        data = {
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='newuser@test.com').exists()

    def test_register_password_mismatch(self, api_client):
        url = reverse('register')
        data = {
            'email': 'newuser2@test.com',
            'password': 'securepass123',
            'password_confirm': 'differentpass',
            'first_name': 'New',
            'last_name': 'User',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_as_admin_denied(self, api_client):
        url = reverse('register')
        data = {
            'email': 'fakeadmin@test.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'first_name': 'Fake',
            'last_name': 'Admin',
            'role': 'admin',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, api_client, customer_user):
        url = reverse('login')
        data = {'email': 'customer@eticket.com', 'password': 'custpass123'}
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data

    def test_login_wrong_password(self, api_client, customer_user):
        url = reverse('login')
        data = {'email': 'customer@eticket.com', 'password': 'wrongpass'}
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        url = reverse('login')
        data = {'email': 'nobody@test.com', 'password': 'somepass'}
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, customer_user):
        login_url = reverse('login')
        login_data = {'email': 'customer@eticket.com', 'password': 'custpass123'}
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']

        refresh_url = reverse('token_refresh')
        response = api_client.post(refresh_url, {'refresh': refresh_token}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_get_profile(self, authenticated_client):
        url = reverse('profile')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'customer@eticket.com'

    def test_update_profile(self, authenticated_client):
        url = reverse('profile')
        response = authenticated_client.patch(url, {'first_name': 'Updated', 'phone': '1234567890'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

    def test_change_password(self, authenticated_client, customer_user):
        url = reverse('change_password')
        data = {
            'old_password': 'custpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.check_password('newpass123')

    def test_change_password_wrong_old(self, authenticated_client):
        url = reverse('change_password')
        data = {
            'old_password': 'wrongold',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_request(self, api_client, customer_user):
        url = reverse('password_reset')
        response = api_client.post(url, {'email': 'customer@eticket.com'}, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_profile_denied(self, api_client):
        url = reverse('profile')
        response = api_client.get(url)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestUserViewSet:
    def test_admin_can_list_users(self, admin_client, customer_user, agent_user):
        url = reverse('user-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 2

    def test_customer_cannot_list_users(self, authenticated_client):
        url = reverse('user-list')
        response = authenticated_client.get(url)
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_retrieve_user(self, admin_client, customer_user):
        url = reverse('user-detail', kwargs={'pk': customer_user.id})
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'customer@eticket.com'

    def test_admin_can_update_user(self, admin_client, customer_user):
        url = reverse('user-detail', kwargs={'pk': customer_user.id})
        response = admin_client.patch(url, {'first_name': 'Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        customer_user.refresh_from_db()
        assert customer_user.first_name == 'Updated'

    def test_admin_can_delete_user(self, admin_client, customer_user):
        url = reverse('user-detail', kwargs={'pk': customer_user.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=customer_user.id).exists()
