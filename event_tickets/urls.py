from django.urls import path
from rest_framework.routers import DefaultRouter
from event_tickets.views import (
    EventCategoryViewSet, EventViewSet, BookingViewSet, PaymentViewSet,
)

router = DefaultRouter()
router.register(r'categories', EventCategoryViewSet, basename='event-category')
router.register(r'events', EventViewSet, basename='event')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('bookings/<int:booking_pk>/payments/', PaymentViewSet.as_view({
        'get': 'list',
        'post': 'create_payment',
    }), name='booking-payments'),
    path('bookings/<int:booking_pk>/payments/<int:pk>/', PaymentViewSet.as_view({
        'get': 'retrieve',
    }), name='payment-detail'),
]

urlpatterns += router.urls
