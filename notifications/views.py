from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'type', 'title', 'message', 'related_object_id', 'is_read', 'created_at')
        read_only_fields = ('id', 'created_at')


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'message': 'Notification marked as read.'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
