from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    SupportCategoryViewSet,
    SupportTicketViewSet,
)

router = SimpleRouter()
router.register(r'categories', SupportCategoryViewSet, basename='support-category')
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')

urlpatterns = router.urls