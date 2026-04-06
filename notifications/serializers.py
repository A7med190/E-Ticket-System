from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'message',
            'related_object_id',
            'is_read',
            'created_at',
            'time_ago',
        ]
        read_only_fields = ['id', 'type', 'title', 'message', 'related_object_id', 'created_at']

    def get_time_ago(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class NotificationListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'is_read',
            'created_at',
        ]


class NotificationMarkReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    mark_all = serializers.BooleanField(default=False)


class NotificationPreferenceSerializer(serializers.Serializer):
    ticket_created = serializers.BooleanField(default=True)
    ticket_assigned = serializers.BooleanField(default=True)
    ticket_status_changed = serializers.BooleanField(default=True)
    ticket_comment = serializers.BooleanField(default=True)
    booking_confirmed = serializers.BooleanField(default=True)
    booking_cancelled = serializers.BooleanField(default=True)
    event_reminder = serializers.BooleanField(default=True)
    payment_completed = serializers.BooleanField(default=True)
    password_reset = serializers.BooleanField(default=True)
    email_verification = serializers.BooleanField(default=True)
