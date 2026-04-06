from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class SupportCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_categories'
        verbose_name_plural = 'Support Categories'
        ordering = ('name',)

    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In Progress')
        WAITING = 'waiting', _('Waiting for Customer')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        CRITICAL = 'critical', _('Critical')

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    category = models.ForeignKey(SupportCategory, on_delete=models.PROTECT, related_name='tickets')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reported_tickets')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['reporter']),
            models.Index(fields=['assignee']),
        ]

    def __str__(self):
        return f'{self.ticket_number} - {self.title}'


class TicketComment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ticket_comments'
        ordering = ('created_at',)

    def __str__(self):
        return f'Comment by {self.author} on {self.ticket.ticket_number}'


class TicketAttachment(models.Model):
    file = models.FileField(upload_to='tickets/attachments/')
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    comment = models.ForeignKey(TicketComment, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_attachments'
        ordering = ('-uploaded_at',)

    def __str__(self):
        return f'Attachment for {self.ticket or self.comment}'
