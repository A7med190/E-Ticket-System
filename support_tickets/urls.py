from django.urls import path
from rest_framework.routers import DefaultRouter
from support_tickets.views import (
    SupportCategoryViewSet, SupportTicketViewSet,
    TicketCommentViewSet, TicketAttachmentViewSet,
)

router = DefaultRouter()
router.register(r'categories', SupportCategoryViewSet, basename='support-category')
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')

urlpatterns = [
    path('tickets/<int:ticket_pk>/comments/', TicketCommentViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='ticket-comments'),
    path('tickets/<int:ticket_pk>/comments/<int:pk>/', TicketCommentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='ticket-comment-detail'),
    path('tickets/<int:ticket_pk>/attachments/', TicketAttachmentViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='ticket-attachments'),
    path('tickets/<int:ticket_pk>/attachments/<int:pk>/', TicketAttachmentViewSet.as_view({
        'get': 'retrieve',
        'delete': 'destroy',
    }), name='ticket-attachment-detail'),
]

urlpatterns += router.urls
