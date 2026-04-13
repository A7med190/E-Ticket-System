import logging
import uuid
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, user=None):
        self.user = user

    def create_ticket(
        self,
        reporter_id: int,
        subject: str,
        description: str,
        priority: str = 'medium',
        category: str = 'general',
        assigned_to_id: int = None,
    ) -> dict:
        from support_tickets.models import SupportTicket
        from accounts.models import User
        from common.services.notification_service import notification_service

        reporter = User.objects.get(id=reporter_id)
        ticket_number = f'SUP-{uuid.uuid4().hex[:8].upper()}'

        with transaction.atomic():
            ticket = SupportTicket.objects.create(
                ticket_number=ticket_number,
                reporter=reporter,
                subject=subject,
                description=description,
                priority=priority,
                category=category,
                status='open',
            )

            if assigned_to_id:
                ticket.assignee_id = assigned_to_id
                ticket.status = 'in_progress'
                ticket.save()

        notification_service.notify_ticket_created(ticket)

        if assigned_to_id:
            ticket.refresh_from_db()
            notification_service.notify_ticket_assigned(ticket)

        return {'ticket': ticket}

    def assign_ticket(self, ticket_id: int, assignee_id: int) -> dict:
        from support_tickets.models import SupportTicket
        from accounts.models import User
        from common.services.notification_service import notification_service

        ticket = SupportTicket.objects.get(id=ticket_id)
        assignee = User.objects.get(id=assignee_id)

        if ticket.assignee_id == assignee_id:
            raise ValidationError('Ticket is already assigned to this user')

        old_assignee_id = ticket.assignee_id

        with transaction.atomic():
            ticket.assignee = assignee
            if ticket.status == 'open':
                ticket.status = 'in_progress'
            ticket.save()

        notification_service.notify_ticket_assigned(ticket)

        return {'ticket': ticket, 'previous_assignee_id': old_assignee_id}

    def update_ticket_status(
        self,
        ticket_id: int,
        new_status: str,
        comment: str = None,
        user_id: int = None,
    ) -> dict:
        from support_tickets.models import SupportTicket, TicketComment
        from common.services.notification_service import notification_service

        valid_statuses = ['open', 'in_progress', 'pending', 'resolved', 'closed']
        if new_status not in valid_statuses:
            raise ValidationError(f'Invalid status. Must be one of: {valid_statuses}')

        ticket = SupportTicket.objects.get(id=ticket_id)
        old_status = ticket.status

        with transaction.atomic():
            ticket.status = new_status
            if new_status == 'closed':
                ticket.closed_at = ticket.updated_at
            ticket.save()

            if comment and user_id:
                TicketComment.objects.create(
                    ticket=ticket,
                    author_id=user_id,
                    content=comment,
                    is_internal=True,
                )

        if old_status != new_status:
            notification_service.notify_ticket_status_changed(ticket)

        return {'ticket': ticket, 'old_status': old_status}

    def add_comment(
        self,
        ticket_id: int,
        user_id: int,
        content: str,
        is_internal: bool = False,
    ) -> dict:
        from support_tickets.models import SupportTicket, TicketComment

        ticket = SupportTicket.objects.get(id=ticket_id)
        comment = TicketComment.objects.create(
            ticket=ticket,
            author_id=user_id,
            content=content,
            is_internal=is_internal,
        )
        return {'comment': comment}

    def escalate_ticket(self, ticket_id: int, reason: str) -> dict:
        from support_tickets.models import SupportTicket
        from common.services.notification_service import notification_service

        ticket = SupportTicket.objects.get(id=ticket_id)

        with transaction.atomic():
            priority_map = {'low': 'medium', 'medium': 'high', 'high': 'critical'}
            new_priority = priority_map.get(ticket.priority, 'critical')
            ticket.priority = new_priority
            ticket.save()

        notification_service.create_in_app_notification(
            user_id=ticket.reporter_id,
            title=f'Ticket {ticket.ticket_number} Escalated',
            message=f'Your ticket has been escalated due to: {reason}',
            notification_type='ticket',
            related_object_type='ticket',
            related_object_id=ticket.id,
        )

        return {'ticket': ticket, 'previous_priority': ticket.priority}


ticket_service = TicketService()
