from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from common.permissions import IsAdmin, IsAgentOrAdmin, IsTicketReporterOrAssigneeOrAdmin, IsCommentAuthorOrTicketParticipant
from common.filters import SupportTicketFilter
from common.utils import export_to_csv
from support_tickets.models import SupportCategory, SupportTicket, TicketComment, TicketAttachment
from support_tickets.serializers import (
    SupportCategorySerializer, SupportTicketSerializer, SupportTicketListSerializer,
    SupportTicketCreateSerializer, TicketCommentSerializer, TicketAttachmentSerializer,
    TicketStatusUpdateSerializer,
)
from support_tickets.services import assign_ticket
from notifications.services import create_notification


class SupportCategoryViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = SupportCategory.objects.all()
    serializer_class = SupportCategorySerializer
    permission_classes = (IsAuthenticated,)
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'created_at')
    ordering = ('name',)


class SupportTicketViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = SupportTicketFilter
    search_fields = ('title', 'description', 'ticket_number')
    ordering_fields = ('created_at', 'updated_at', 'priority', 'status')
    ordering = ('-created_at',)

    def get_queryset(self):
        user = self.request.user
        qs = SupportTicket.objects.select_related('category', 'reporter', 'assignee')
        if user.role == 'admin':
            return qs
        if user.role in ('agent', 'organizer'):
            return qs.filter(Q(assignee=user) | Q(reporter=user))
        return qs.filter(reporter=user)

    def get_serializer_class(self):
        if self.action == 'list':
            return SupportTicketListSerializer
        if self.action == 'create':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        ticket = serializer.save()
        assign_ticket(ticket)
        create_notification(
            user=ticket.reporter,
            notification_type='ticket_created',
            title='Ticket Created',
            message=f'Your ticket {ticket.ticket_number} has been created.',
            related_object_id=str(ticket.id),
        )
        if ticket.assignee:
            create_notification(
                user=ticket.assignee,
                notification_type='ticket_assigned',
                title='New Ticket Assigned',
                message=f'You have been assigned ticket {ticket.ticket_number}.',
                related_object_id=str(ticket.id),
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAgentOrAdmin])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        agent_id = request.data.get('agent_id')
        if agent_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                agent = User.objects.get(id=agent_id, role__in=['agent', 'admin'])
                ticket.assignee = agent
                ticket.save(update_fields=['assignee', 'updated_at'])
                create_notification(
                    user=agent,
                    notification_type='ticket_assigned',
                    title='Ticket Assigned',
                    message=f'You have been assigned ticket {ticket.ticket_number}.',
                    related_object_id=str(ticket.id),
                )
                return Response({'message': f'Ticket assigned to {agent.email}'})
            except User.DoesNotExist:
                return Response({'error': 'Agent not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'agent_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAgentOrAdmin])
    def change_status(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = ticket.status
        ticket.status = serializer.validated_data['status']

        if ticket.status == SupportTicket.Status.RESOLVED and old_status != SupportTicket.Status.RESOLVED:
            ticket.resolved_at = timezone.now()

        ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])

        comment_body = serializer.validated_data.get('comment', '')
        if comment_body:
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=comment_body,
                is_internal=False,
            )

        create_notification(
            user=ticket.reporter,
            notification_type='ticket_status_changed',
            title='Ticket Status Updated',
            message=f'Ticket {ticket.ticket_number} status changed from {old_status} to {ticket.status}.',
            related_object_id=str(ticket.id),
        )
        return Response({'message': 'Status updated.', 'status': ticket.status})

    @action(detail=False, methods=['get'], permission_classes=[IsAgentOrAdmin])
    def stats(self, request):
        qs = self.get_queryset()
        total = qs.count()
        by_status = dict(qs.values_list('status').annotate(count=Count('status')))
        by_priority = dict(qs.values_list('priority').annotate(count=Count('priority')))
        resolved = qs.filter(resolved_at__isnull=False)
        avg_resolution = resolved.aggregate(avg=Avg('resolved_at'))['avg']

        return Response({
            'total': total,
            'by_status': by_status,
            'by_priority': by_priority,
            'avg_resolution_time_hours': avg_resolution.total_seconds() / 3600 if avg_resolution else None,
            'open_count': by_status.get('open', 0),
            'in_progress_count': by_status.get('in_progress', 0),
            'resolved_count': by_status.get('resolved', 0),
            'closed_count': by_status.get('closed', 0),
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAgentOrAdmin])
    def export(self, request):
        qs = self.get_queryset()
        field_names = ('ticket_number', 'title', 'status', 'priority', 'category', 'reporter', 'assignee', 'created_at', 'resolved_at')
        return export_to_csv(qs, field_names, 'support_tickets')


class TicketCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketCommentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_pk')
        qs = TicketComment.objects.filter(ticket_id=ticket_id).select_related('author')
        if self.request.user.role == 'customer':
            qs = qs.filter(is_internal=False)
        return qs

    def perform_create(self, serializer):
        ticket = SupportTicket.objects.get(id=self.kwargs.get('ticket_pk'))
        serializer.save(
            author=self.request.user,
            ticket=ticket,
        )
        if ticket.assignee and ticket.assignee != self.request.user:
            create_notification(
                user=ticket.assignee,
                notification_type='ticket_comment',
                title='New Comment',
                message=f'New comment on ticket {ticket.ticket_number}.',
                related_object_id=str(ticket.id),
            )
        if ticket.reporter and ticket.reporter != self.request.user:
            create_notification(
                user=ticket.reporter,
                notification_type='ticket_comment',
                title='New Comment',
                message=f'New comment on ticket {ticket.ticket_number}.',
                related_object_id=str(ticket.id),
            )


class TicketAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketAttachmentSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_pk')
        return TicketAttachment.objects.filter(ticket_id=ticket_id)

    def perform_create(self, serializer):
        ticket = SupportTicket.objects.get(id=self.kwargs.get('ticket_pk'))
        comment_id = self.request.data.get('comment_id')
        comment = None
        if comment_id:
            comment = TicketComment.objects.get(id=comment_id, ticket=ticket)
        serializer.save(
            ticket=ticket,
            comment=comment,
            uploaded_by=self.request.user,
        )
