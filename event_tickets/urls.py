from django.urls import path
from rest_framework.routers import SimpleRouter
from event_tickets.views import (
    EventCategoryViewSet, EventViewSet, BookingViewSet, PaymentViewSet,
)

router = SimpleRouter()
router.register(r'categories', EventCategoryViewSet, basename='event-category')
router.register(r'events', EventViewSet, basename='event')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = router.urls