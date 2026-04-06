from django.contrib.auth import get_user_model
from support_tickets.models import SupportTicket

User = get_user_model()


def assign_ticket(ticket):
    if ticket.assignee:
        return ticket.assignee

    agents = User.objects.filter(role__in=['agent', 'admin'], is_active=True)
    if not agents.exists():
        return None

    agent_counts = {}
    for agent in agents:
        count = SupportTicket.objects.filter(assignee=agent, status__in=['open', 'in_progress']).count()
        agent_counts[agent] = count

    min_count = min(agent_counts.values())
    for agent, count in agent_counts.items():
        if count == min_count:
            ticket.assignee = agent
            ticket.save(update_fields=['assignee', 'updated_at'])
            return agent

    return None
