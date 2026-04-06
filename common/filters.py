import django_filters
from django.db.models import Q


class SupportTicketFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    priority = django_filters.CharFilter(field_name='priority')
    category = django_filters.NumberFilter(field_name='category_id')
    assignee = django_filters.NumberFilter(field_name='assignee_id')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        fields = ['status', 'priority', 'category', 'assignee']


class EventFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category_id')
    organizer = django_filters.NumberFilter(field_name='organizer_id')
    is_published = django_filters.BooleanFilter(field_name='is_published')
    start_after = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_before = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')

    class Meta:
        fields = ['category', 'organizer', 'is_published']


class BookingFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    event = django_filters.NumberFilter(field_name='event_id')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        fields = ['status', 'event']
