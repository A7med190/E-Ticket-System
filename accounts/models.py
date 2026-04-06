from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        AGENT = 'agent', _('Agent')
        CUSTOMER = 'customer', _('Customer')
        ORGANIZER = 'organizer', _('Event Organizer')

    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, default='')
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_agent(self):
        return self.role == self.Role.AGENT

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER
